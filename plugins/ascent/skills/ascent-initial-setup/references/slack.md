# Slack messaging workflow

Use this reference only when the client uses Slack.

## Locate Slack context

- Use `slack_search_channels` to find likely existing channels by the user-provided known-channel name, account, project, project, or engagement name. Search the provided term as written first; the connector search is term-based, not an exact-match assertion.
- Search public and private channels when the user indicates both may be in play. Prefer exact or near-exact name matches before broader topical matches.
- When the channel-metadata result is empty but the user says a matching source exists, ask for explicit consent before searching conversations. With consent, use `slack_search_public_and_private` for the same term across public channels, private channels, DMs, and group DMs; request no surrounding context and report only matched conversation locations, not message text or file contents.
- If both the metadata and consented conversation searches are empty, record the probe as scope not verified. Direct the user through the host's plugin or connector settings, select Slack, choose **Connect**, and complete sign-in with the intended work account. If the connection still lacks the expected source, ask a workspace admin to review app enablement, role access, domain restrictions, and provider permissions. Rerun the same searches after reconnection. Do not give shell commands.
- Report the best candidates with channel name, purpose or topic when available, whether the channel is archived, and the account, project, or workstream terms that matched.
- For confirmed channels, the project communications record may include channel name, available channel ID, purpose or topic, and archived state.
