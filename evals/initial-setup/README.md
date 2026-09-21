# Initial-setup evaluation

This regression package checks two high-risk contracts: all supported storage decisions remain routable, and the readiness verdict reflects the state of a freshly initialized Opportunity, including identity metadata.

Run it with:

```bash
python3 evals/initial-setup/run_deterministic.py
```

The runner uses a fresh temporary directory, redirects `HOME`, blocks network APIs in subprocesses, and does not install dependencies. It grades concepts and filesystem state rather than exact documentation wording.

This deterministic package does not answer model cost, a no-skill baseline, human time saved, or agent behavior. Those remain explicit gaps: `no-cost-data`, `no-baseline-arm`, `no-human-baseline`, and `behavior-not-observable`.
