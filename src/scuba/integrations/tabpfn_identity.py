"""Reviewed response identities; no filename-prefix or arbitrary path matching."""

# See docs/M3_CHECKPOINT_RESOLUTION.md for pinned official sources and scope.
PLUS_CHECKPOINT = "/app/tabpfn_models/tabpfn-v3.5-20260909.safetensors"
IDENTITY_POLICY = "plus-checkpoint-20260909-v1"


def class_order_matches(plan, metadata):
    classes = metadata.get("classes")
    return plan["class_order"] == [0, 1] and (
        "classes" not in metadata
        or (
            isinstance(classes, list)
            and all(type(value) is int for value in classes)
            and classes == [0, 1]
        )
    )


def checked_identity(config, metadata):
    reported = metadata.get("tabpfn_config")
    path = reported.get("model_path") if isinstance(reported, dict) else None
    if isinstance(path, str) and path == config.model_path:
        return "exact_requested_alias"
    if (
        config.variant == "plus"
        and config.model_path == "v3.5_default"
        and path == PLUS_CHECKPOINT
        and metadata.get("billing_model_version") == "v3.5"
        and metadata.get("execution_mode") == "standard"
        and "classes" in metadata
        and class_order_matches({"class_order": [0, 1]}, metadata)
    ):
        return IDENTITY_POLICY
    return None
