# Bootstrap administration through a seed command

Public registration creates only Standard Users. A seed command creates the initial Administrator, preventing self-assigned administrative authority. A future protected `POST /api/users/{id}/promote` endpoint may let an existing Administrator promote a Standard User; it will return the safe User Account representation and be idempotent for an existing Administrator, but it is not part of the initial release.
