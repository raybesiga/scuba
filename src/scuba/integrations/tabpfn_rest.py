"""Bounded synchronous TabPFN REST transport; explicit approval before uploads."""

import hashlib
import logging
import re
import time
from dataclasses import asdict, dataclass
from urllib.parse import urlsplit
from uuid import UUID

import httpx
import numpy as np

from scuba.integrations.tabpfn_evidence import field_inventory, reported_fields
from scuba.integrations.tabpfn_identity import checked_identity, class_order_matches
from scuba.integrations.tabpfn_plan import (
    TabPFNConfig,
    check_limits,
    checked_estimate,
    plan_digest,
    prediction_rows,
)
from scuba.integrations.tabpfn_response_archive import archive_response

API_ORIGIN = "https://api.priorlabs.ai"


@dataclass
class IntegrationError(Exception):
    category: str
    status_code: int | None = None
    billing_uncertain: bool = False

    def __str__(self):
        return f"TabPFN integration stopped: {self.category}"

    def evidence(self):
        return asdict(self)


def resource_id(value):
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise IntegrationError("invalid_resource_id") from None


class TabPFNRest:
    def __init__(self, token: str, *, transport=None):
        if not token or any(c.isspace() for c in token):
            raise IntegrationError("missing_or_invalid_token")
        # Prevent HTTP libraries from logging signed storage URLs in verbose sessions.
        for name in ("httpx", "httpcore"):
            logging.getLogger(name).setLevel(logging.WARNING)
        self._token = token
        self._client = httpx.Client(
            transport=transport,
            timeout=httpx.Timeout(30, connect=10),
            follow_redirects=False,
            trust_env=False,
        )
        self.stages = []
        self.billing_uncertain = False
        self.prediction_evidence = None
        self.execution_evidence = None
        self._prediction_attempted = False
        self.response_archive_dir = None
        self.prediction_response_archive = None

    def close(self):
        self._client.close()

    def _request(
        self,
        method,
        url,
        *,
        stage,
        body=None,
        content=None,
        headers=None,
        billable=False,
        accept_conflict=False,
        timeout=30,
    ):
        start = time.perf_counter()
        if billable:
            self.billing_uncertain = True
        try:
            chunks = []
            size = 0
            with self._client.stream(
                method,
                url,
                json=body,
                content=content,
                headers=headers,
                # Signed data transfers can take longer than metadata requests.
                # Prediction streams retain their shorter idle-read timeout.
                timeout=httpx.Timeout(
                    timeout if content is not None else min(timeout, 30), connect=10
                ),
            ) as stream:
                for chunk in stream.iter_bytes():
                    if time.perf_counter() - start > timeout:
                        raise httpx.ReadTimeout("operation deadline exceeded")
                    size += len(chunk)
                    if size > 64 * 1024 * 1024:
                        raise IntegrationError("response_too_large", billing_uncertain=billable)
                    chunks.append(chunk)
                response = httpx.Response(
                    stream.status_code, headers=stream.headers, content=b"".join(chunks)
                )
        except httpx.TimeoutException:
            raise IntegrationError("timeout", billing_uncertain=billable) from None
        except httpx.HTTPError:
            raise IntegrationError("transport_failure", billing_uncertain=billable) from None
        finally:
            self.stages.append({"stage": stage, "elapsed_seconds": time.perf_counter() - start})
        if stage == "predict" and self.response_archive_dir is not None:
            self.prediction_response_archive = archive_response(
                self.response_archive_dir, response, secrets=(self._token,)
            )
        if response.status_code == 409 and accept_conflict:
            return response
        if not 200 <= response.status_code < 300:
            status = response.status_code
            category = {
                401: "authentication",
                403: "access_denied",
                404: "not_found",
                409: "conflict",
                422: "schema_or_data",
                429: "quota_or_rate_limit",
            }.get(status, "http_failure")
            if status == 429:
                # Classify only; never retain or print a remote error body.
                text = response.text.lower()
                if any(word in text for word in ("quota", "daily", "monthly", "token budget")):
                    category = "quota_exhausted"
                elif "rate" in text:
                    category = "rate_limit"
            raise IntegrationError(category, status, billable)
        return response

    def _api(self, method, path, *, body=None, billable=False, accept_conflict=False, timeout=30):
        response = self._request(
            method,
            API_ORIGIN + path,
            stage=path.rsplit("/", 1)[-1],
            body=body,
            headers={"Authorization": f"Bearer {self._token}"},
            billable=billable,
            accept_conflict=accept_conflict,
            timeout=timeout,
        )
        try:
            result = response.json()  # Also accepts leading streamed keepalive whitespace.
            if not isinstance(result, dict):
                raise ValueError
        except (ValueError, TypeError):
            raise IntegrationError("invalid_json", billing_uncertain=billable) from None
        return response.status_code, result

    def preflight(self, plan):
        _, limits = self._api("GET", "/tabpfn/get_model_limits")
        try:
            checked_limits = check_limits(plan, limits)
            estimates = []
            for request in plan["estimate_requests"]:
                _, response = self._api("POST", "/tabpfn/estimate_cost", body=request)
                estimates.append(checked_estimate(request, response))
        except (ValueError, KeyError, TypeError):
            raise IntegrationError("preflight_contract_or_limit") from None
        return {
            "evidence": "live_metadata_only",
            "plan_sha256": plan_digest(plan),
            "checked_at_unix": time.time(),
            "model_limits": checked_limits,
            "estimates": estimates,
            "estimated_total_tokens": sum(e["estimated_tokens"] for e in estimates),
            "actual_tokens": 0,
            "rows_uploaded": 0,
        }

    def _upload(self, info, payload, stage):
        try:
            urls, headers = info["signed_urls"], info["required_headers"]
            if (
                not isinstance(urls, list)
                or len(urls) != 1
                or not isinstance(headers, dict)
                or not all(isinstance(k, str) and isinstance(v, str) for k, v in headers.items())
                or any(k.lower() in ("authorization", "cookie") for k in headers)
                or not isinstance(info["expires_at"], (int, float))
                or info["expires_at"] <= time.time()
            ):
                raise ValueError
            url = urlsplit(urls[0])
            if (
                url.scheme != "https"
                or url.username
                or url.password
                or url.port not in (None, 443)
                or not url.hostname
                or not (
                    url.hostname == "storage.googleapis.com"
                    or url.hostname.endswith(".storage.googleapis.com")
                )
            ):
                raise ValueError
            # GCS signatures may require Host. Permit it only when it matches
            # the already-validated URL authority; never allow host redirection.
            hosts = [v for k, v in headers.items() if k.lower() == "host"]
            if len(hosts) > 1 or (hosts and hosts[0].lower() != url.netloc.lower()):
                raise ValueError
        except (KeyError, TypeError, ValueError, AttributeError):
            raise IntegrationError("unsupported_signed_upload") from None
        self._request("PUT", urls[0], stage=stage, content=payload, headers=headers, timeout=180)

    def execute(self, plan, payloads, *, allow_upload=False, max_tokens=None, response_sink=None):
        if not allow_upload or type(max_tokens) is not int or max_tokens <= 0:
            raise IntegrationError("upload_and_positive_budget_approval_required")
        if self._prediction_attempted:
            raise IntegrationError("prediction_already_attempted", billing_uncertain=True)
        partition = plan.get("prediction_partition", "validation")
        if partition not in ("validation", "test") or set(payloads) != {
            "train",
            "labels",
            partition,
        }:
            raise IntegrationError("unsupported_prediction_payloads")
        from scuba.integrations.tabpfn_plan import digest

        if set(payloads) != set(plan["payloads"]) or any(
            digest(payload) != plan["payloads"][name]["sha256"]
            for name, payload in payloads.items()
        ):
            raise IntegrationError("payload_changed")
        if plan.get("classification") not in (
            "synthetic",
            "external_challenge_data_origin_unverified",
        ):
            raise IntegrationError("unsupported_data_classification")
        fresh = self.preflight(plan)
        self.execution_evidence = {
            "fresh_preflight": fresh,
            "approved_estimate_budget": max_tokens,
            "actual_tokens": None,
        }
        if fresh["estimated_total_tokens"] > max_tokens:
            raise IntegrationError("approved_estimate_budget_exceeded")
        # Fresh limits/costs are checked immediately before the first upload request.
        config = TabPFNConfig(**plan["configuration"])
        if plan["fit_parameters"] != config.fit_parameters():
            raise IntegrationError("plan_configuration_changed")

        def info(name):
            return {
                "format": "csv",
                "size_bytes": len(payloads[name]),
                "use_chunks": False,
            }

        status, prepared = self._api(
            "POST",
            "/tabpfn/prepare_train_set_upload",
            body={
                "x_train_info": info("train"),
                "y_train_info": info("labels"),
                "description": (
                    "SCUBA Financial Stress challenge snapshots; real/synthetic origin unverified."
                    if plan["classification"] == "external_challenge_data_origin_unverified"
                    else "SCUBA: entirely synthetic development cohort; no real customer data."
                ),
            },
            accept_conflict=True,
        )
        train_id = resource_id(prepared.get("train_set_upload_id"))
        if status != 409:
            self._upload(prepared.get("x_train_info"), payloads["train"], "upload_train_features")
            self._upload(prepared.get("y_train_info"), payloads["labels"], "upload_train_labels")
        _, fit = self._api(
            "POST",
            "/tabpfn/fit",
            body={**plan["fit_parameters"], "train_set_upload_id": train_id},
            billable=config.variant == "thinking",
            timeout=330,
        )
        fitted_id = resource_id(fit.get("fitted_train_set_id"))
        self.execution_evidence["fitted_train_set_id"] = fitted_id
        status, prepared = self._api(
            "POST",
            "/tabpfn/prepare_test_set_upload",
            body={"fitted_train_set_id": fitted_id, "x_test_info": info(partition)},
            accept_conflict=True,
        )
        test_id = resource_id(prepared.get("test_set_upload_id"))
        self.execution_evidence["test_set_upload_id"] = test_id
        if status != 409:
            self._upload(
                prepared.get("x_test_info"), payloads[partition], f"upload_{partition}_features"
            )
        return self._predict_prepared(plan, fitted_id, test_id, fresh, max_tokens, response_sink)

    def predict_existing(
        self, plan, fitted_id, test_id, *, allow_predict=False, max_tokens=None, response_sink=None
    ):
        """One approved Plus prediction using existing resources; never upload or fit."""
        if not allow_predict or type(max_tokens) is not int or max_tokens <= 0:
            raise IntegrationError("prediction_and_positive_budget_approval_required")
        if self._prediction_attempted:
            raise IntegrationError("prediction_already_attempted", billing_uncertain=True)
        fitted_id, test_id = resource_id(fitted_id), resource_id(test_id)
        config = TabPFNConfig(**plan["configuration"])
        if config.variant != "plus" or plan["fit_parameters"] != config.fit_parameters():
            raise IntegrationError("unsupported_continuation_configuration")
        fresh = self.preflight(plan)
        self.execution_evidence = {
            "fresh_preflight": fresh,
            "approved_estimate_budget": max_tokens,
            "actual_tokens": None,
            "fitted_train_set_id": fitted_id,
            "test_set_upload_id": test_id,
            "mode": "prediction_only",
            "rows_uploaded": 0,
        }
        if fresh["estimated_total_tokens"] > max_tokens:
            raise IntegrationError("approved_estimate_budget_exceeded")
        return self._predict_prepared(plan, fitted_id, test_id, fresh, max_tokens, response_sink)

    def predict_final_test(
        self, plan, payload, *, allow_upload=False, max_tokens=None, response_sink=None
    ):
        """Upload one held-out feature table and predict once; reuse the fitted model."""
        if not allow_upload or type(max_tokens) is not int or max_tokens <= 0:
            raise IntegrationError("upload_and_positive_budget_approval_required")
        if self._prediction_attempted:
            raise IntegrationError("prediction_already_attempted", billing_uncertain=True)
        config = TabPFNConfig(**plan["configuration"])
        if (
            plan.get("schema") != "scuba.tabpfn-final-plan/v1"
            or plan.get("prediction_partition") != "test"
            or config.variant != "plus"
            or config.fit_parameters() != plan["fit_parameters"]
            or hashlib.sha256(payload).hexdigest() != plan["payloads"]["test"]["sha256"]
            or len(payload) != plan["payloads"]["test"]["size_bytes"]
        ):
            raise IntegrationError("approved_plan_changed")
        fitted_id = resource_id(plan["retained_fitted_train_set_id"])
        fresh = self.preflight(plan)
        self.execution_evidence = {
            "fresh_preflight": fresh,
            "approved_estimate_budget": max_tokens,
            "actual_tokens": None,
            "fitted_train_set_id": fitted_id,
            "phase": "final_test",
            "rows_uploaded": 0,
        }
        if fresh["estimated_total_tokens"] > max_tokens:
            raise IntegrationError("approved_estimate_budget_exceeded")
        status, prepared = self._api(
            "POST",
            "/tabpfn/prepare_test_set_upload",
            body={
                "fitted_train_set_id": fitted_id,
                "x_test_info": {"format": "csv", "size_bytes": len(payload), "use_chunks": False},
            },
            accept_conflict=True,
        )
        test_id = resource_id(prepared.get("test_set_upload_id"))
        self.execution_evidence["test_set_upload_id"] = test_id
        if status != 409:
            self._upload(prepared.get("x_test_info"), payload, "upload_final_test_features")
            self.execution_evidence["rows_uploaded"] = prediction_rows(plan)
        return self._predict_prepared(plan, fitted_id, test_id, fresh, max_tokens, response_sink)

    def _predict_prepared(self, plan, fitted_id, test_id, fresh, max_tokens, response_sink):
        if self._prediction_attempted:
            raise IntegrationError("prediction_already_attempted", billing_uncertain=True)
        self._prediction_attempted = True
        config = TabPFNConfig(**plan["configuration"])
        _, response = self._api(
            "POST",
            "/tabpfn/predict",
            body={
                "test_set_upload_id": test_id,
                "fitted_train_set_id": fitted_id,
                "task_config": {
                    "task": "classification",
                    "tabpfn_config": config.model_parameters(),
                    "predict_params": {"output_type": "probas"},
                },
            },
            billable=True,
            timeout=330,
        )
        self.prediction_evidence = prediction_diagnostics(plan, response, secrets=(self._token,))
        if self.prediction_response_archive is not None:
            self.prediction_evidence["complete_response_archive"] = self.prediction_response_archive
        if response_sink is not None:
            response_sink(self.prediction_evidence)
        # A malformed version can look syntactically valid while echoing a secret.
        package = self.prediction_evidence["reported_metadata"]["package_version"]
        if package["status"] != "retained":
            raise IntegrationError("prediction_contract", billing_uncertain=True)
        probability, metadata = validate_prediction(plan, response)
        # Only sanitised observations may enter the persisted success manifest.
        metadata["package_version"] = package["value"]
        metadata["tabpfn_config"] = {
            name: field["value"]
            for name, field in self.prediction_evidence["reported_configuration"].items()
        }
        return probability, {
            "fresh_preflight": fresh,
            "requested_variant": config.variant,
            "server_metadata": metadata,
            "fitted_train_set_id": fitted_id,
            "stages": self.stages.copy(),
            "actual_tokens": None,
            "actual_tokens_reason": "Published prediction response has no per-operation token charge.",
            "approved_estimate_budget": max_tokens,
            "checkpoint_identity": metadata["identity_validation"],
        }


def prediction_diagnostics(plan, response, *, secrets=()):
    """Keep bounded, unverified evidence without arbitrary server strings/bodies."""
    config = TabPFNConfig(**plan["configuration"])
    meta = response.get("metadata")
    meta = meta if isinstance(meta, dict) else {}
    reported = meta.get("tabpfn_config")
    reported = reported if isinstance(reported, dict) else {}
    observed_config = reported_fields(reported, config.model_parameters(), secrets=secrets)
    observed_metadata = reported_fields(
        meta,
        (
            "task",
            "test_set_num_rows",
            "test_set_num_cols",
            "package_version",
            "billing_model_version",
            "execution_mode",
            "cache_outcome",
            "classes",
        ),
        secrets=secrets,
    )
    package = meta.get("package_version")
    checks = {
        "probabilities": False,
        "task": meta.get("task", "classification") == "classification",
        "rows": meta.get("test_set_num_rows") == prediction_rows(plan),
        "columns": meta.get("test_set_num_cols") == len(plan["feature_columns"]),
        "package_version": isinstance(package, str)
        and len(package) <= 128
        and bool(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+[A-Za-z0-9.+_-]*", package)),
        "model_path": checked_identity(config, meta) is not None,
        "class_order": class_order_matches(plan, meta),
    }
    if config.variant != "thinking":
        checks.update(
            {
                key: reported.get(key) == value
                for key, value in config.model_parameters().items()
                if key != "model_path"
            }
        )
    evidence = {
        "status": "unverified_response",
        "capture_format": "filtered_diagnostics_with_field_inventory_v2",
        "raw_response_preserved": False,
        "response_field_inventory": {
            "top_level": field_inventory(response, secrets=secrets),
            "metadata": field_inventory(response.get("metadata"), secrets=secrets),
            "configuration": field_inventory(meta.get("tabpfn_config"), secrets=secrets),
        },
        "classification": plan.get("classification", "unknown"),
        "plan_sha256": plan_digest(plan),
        "checks": checks,
        "metadata_fields_present": {
            key: key in meta
            for key in ("task", "test_set_num_rows", "test_set_num_cols", "package_version")
        },
        "configuration_fields_present": {key: key in reported for key in config.model_parameters()},
        "requested_configuration": config.model_parameters(),
        "requested_variant": config.variant,
        "prediction_partition": plan.get("prediction_partition", "validation"),
        "reported_model_identity": observed_config["model_path"],
        "reported_configuration": observed_config,
        "reported_metadata": observed_metadata,
        "metadata_container_type": type(response.get("metadata")).__name__,
        "configuration_container_type": type(meta.get("tabpfn_config")).__name__,
        "prediction": None,
    }
    try:
        matrix = np.asarray(response.get("prediction"), dtype=float)
        if (
            matrix.shape == (prediction_rows(plan), 2)
            and np.isfinite(matrix).all()
            and (matrix >= 0).all()
            and (matrix <= 1).all()
            and np.allclose(matrix.sum(axis=1), 1, atol=1e-6, rtol=0)
        ):
            checks["probabilities"] = True
            evidence["prediction"] = matrix.tolist()
    except (TypeError, ValueError):
        pass
    return evidence


def validate_prediction(plan, response):
    try:
        matrix = np.asarray(response["prediction"], dtype=float)
        rows = prediction_rows(plan)
        if (
            matrix.shape != (rows, 2)
            or not np.isfinite(matrix).all()
            or (matrix < 0).any()
            or (matrix > 1).any()
            or not np.allclose(matrix.sum(axis=1), 1, atol=1e-6, rtol=0)
        ):
            raise ValueError
        meta = response["metadata"]
        config = TabPFNConfig(**plan["configuration"])
        reported = meta["tabpfn_config"]
        if (
            meta.get("task", "classification") != "classification"
            or meta["test_set_num_rows"] != rows
            or meta["test_set_num_cols"] != len(plan["feature_columns"])
            or checked_identity(config, meta) is None
            or not isinstance(meta["package_version"], str)
            or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+[A-Za-z0-9.+_-]*", meta["package_version"])
            or len(meta["package_version"]) > 128
        ):
            raise ValueError
        if config.variant != "thinking" and any(
            reported.get(key) != value
            for key, value in config.model_parameters().items()
            if key != "model_path"
        ):
            raise ValueError
        # Older responses omit classes; SDK uses np.unique(y). If reported,
        # require exact integer class order instead of trusting the local plan.
        if not class_order_matches(plan, meta):
            raise ValueError
        safe = {
            key: meta[key] for key in ("test_set_num_rows", "test_set_num_cols", "package_version")
        }
        safe["tabpfn_config"] = {
            key: reported.get(key)
            for key in ("model_path", "n_estimators", "random_state", "fit_mode")
        }
        safe["identity_validation"] = {
            "policy": checked_identity(config, meta),
            "requested_alias": config.model_path,
            "reported_model_path": reported["model_path"],
            "scope": "server-reported identity; checkpoint bytes not independently attested",
        }
        return matrix[:, 1], safe
    except (KeyError, TypeError, ValueError, AttributeError):
        raise IntegrationError("prediction_contract", billing_uncertain=True) from None
