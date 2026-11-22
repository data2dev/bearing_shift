# Contributing

Thanks for your interest. The project is early; see [ROADMAP.md](ROADMAP.md) for what's planned.

## Licence of contributions

By contributing, you agree that your contribution is licensed under the [Apache License 2.0](LICENSE), as described in section 5 of that licence.

Every commit must carry a [Developer Certificate of Origin](https://developercertificate.org/) sign-off, certifying that you wrote the change or otherwise have the right to submit it under this licence:

```bash
git commit -s -m "Your message"
```

This adds a line like `Signed-off-by: Your Name <you@example.com>`.

## Ground rules

- **Never commit data.** No signals, no processed features from real datasets, no model weights. Use the synthetic generator for tests.
- **Don't copy code** from projects whose licence is incompatible with Apache 2.0 (for example GPL), or from papers' supplementary code without a clear licence.
- **Splits are by bearing.** Any change to evaluation must keep the leakage test passing.
- **Don't change the evaluation protocol silently.** Protocol changes go in their own PR with a changelog note explaining why.
- **Report negative results.** A model that loses to the physics baseline is a result, not a failure.
