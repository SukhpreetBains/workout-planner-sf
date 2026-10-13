# Microsoft Teams messaging workflow

Use this reference only when the client uses Microsoft Teams.

## Locate Teams context

- Use `list_teams` first when the user names a team but the exact team ID is unknown. Request the largest supported result set and inspect it locally for the user-provided term.
- Use `list_channels` after the team is resolved to find the likely channel.
- If no returned team matches a user-identified team or workstream, ask for explicit consent before searching chats and channel conversations. With consent, use `microsoft_teams_search` for the same term across chats and channel threads, then report only matched conversation locations, not message text or file contents.
- If both the metadata and consented conversation searches are empty, record the probe as scope not verified. Direct the user through the host's plugin or connector settings, select Microsoft Teams, choose **Connect**, and complete sign-in with the intended work account. If the connection still lacks the expected source, ask a workspace admin to review app enablement, role access, domain restrictions, and provider permissions. Rerun the same searches after reconnection. If the team appears but the named channel does not, report that separately as a membership or channel-visibility issue. Do not give shell commands.
- Report the best candidates with resolved team and channel names, channel description when available, and the account, project, or workstream terms that matched.
- For confirmed channels, the project communications record may include team name and ID, channel name and ID, and available description.
