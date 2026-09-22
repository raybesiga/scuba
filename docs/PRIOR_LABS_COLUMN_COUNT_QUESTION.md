# Draft question for PriorLabs/tabpfn-client

Status: prepared locally; not posted. Intended destination: a public issue in
https://github.com/PriorLabs/tabpfn-client/issues.

## Title

REST metadata: why does test_set_num_cols change from 182 to 184?

## Body

We are using the documented REST upload → fit → predict workflow with
TabPFN-3.5-Plus (`v3.5_default`, eight estimators, seed 3501,
`fit_preprocessors`, systems `preprocessing` and `text`).

After fitting 40,000 labelled rows and predicting 30,000 unlabelled rows, the
response reports `test_set_num_cols: 184`. Both uploaded feature CSVs have exactly
182 columns. An independent CSV parser checked every row, and the uploaded-byte
hashes match our frozen plan. IDs and targets are excluded from feature uploads;
training labels are uploaded separately as one column.

The response contains 30,000 valid two-class probability rows and reports the
expected checkpoint (`tabpfn-v3.5-20260909.safetensors`), settings and class order.
`package_version` is `9.0.0`. The existing fit-status endpoint reports completed.
We retained the probability matrix and selected metadata fields, not the complete
raw response, and have not repeated prediction. Our old capture omitted unknown
field names, so we cannot establish whether a feature schema was returned.

Update: one explicitly authorised diagnostic has now repeated prediction on the
same existing resources with complete response capture. It returns identical
probabilities and again reports 184. Its body contains only prediction, metadata
and timings; no feature-name schema. The configuration reports categorical indices
`[179, 180, 181]`, while those positions in the uploaded order contain numerical
monthly balance features. Does this metadata refer to a reordered/transformed
representation? No further prediction is planned.

With the same 182 features and configuration, our earlier 24,000-row fit reported
182 columns on both 8,000-row validation and final predictions. All five string
columns have unchanged category sets/cardinalities (2, 7, 2, 3, 3); there are no
missing values or constant features, and no numeric feature crosses the four-value
cardinality boundary when extending training to 40,000 rows.

The current SDK declares this field as an integer but does not define whether
it counts raw inputs, transformed features or a table containing outputs. Both
earlier runs also returned two probability columns but reported 182, so counting
two outputs cannot explain the change as a uniform convention. Could you clarify:

1. At which processing stage is `test_set_num_cols` measured?
2. Can the reported count include generated features or probability outputs in
   some execution paths, and is there a read-only way to retrieve the original
   prediction response or feature schema for existing resources?
3. If the field should describe raw columns, is this a known metadata issue?

We can provide the retained resource IDs through a private support channel if
needed. No dataset records, account details or credentials are included here.
