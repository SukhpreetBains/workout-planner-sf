# Storage Decision Tree

Use this decision tree after asking, **"Is there a shared workspace for this opportunity?"** Ask one question at a time and load only the reference for the selected branch.

## No shared workspace exists

Ask, **"Would you like help setting up a shared workspace or would you prefer to set it up so it's only on your computer?"**

- For a shared workspace, ask, **"Are you using SharePoint for file storage or another cloud storage solution?"** Follow the SharePoint or other-enterprise-storage branch below.
- For **Only on my computer**, offer the Desktop or another user-provided parent folder. Inspect the resolved parent path and say if it is already redirected into cloud storage. Confirm the Account name, Opportunity name, and full proposed path before creating or reusing `<chosen parent>/<Account name>`. Explain that this local-only workspace will not be shared or synchronized automatically.

## A shared workspace exists

Ask, **"In order to work in that space we need to get it synced locally on your machine. Would you like help getting it synced locally?"**

- If yes, ask which storage provider they use. For SharePoint, read [the SharePoint walkthrough](sharepoint-walkthrough.md). For another provider, follow the other-enterprise-storage branch below.
- If no, do not assume a synced path exists. Offer the same local-only flow described above and explain that its files will not automatically appear in the shared workspace.

## Other enterprise storage

Ask, **"What enterprise storage solution are you using?"** Then:

1. Check whether an installed plugin can access that provider. If none is installed, use the host's plugin discovery mechanism when available and offer the exact relevant plugin. Install or connect it only with the user's authorization.
2. Treat plugin access as separate from desktop synchronization. Use the plugin to resolve or verify the shared location when supported, but still obtain a confirmed locally synced path.
3. If no suitable plugin exists, ask for consent before researching the provider. Use authoritative provider documentation to guide its supported desktop sync setup.
4. Do not guess a synced path or treat an ordinary downloaded copy as synchronized storage. Confirm the local path and write readiness.
5. If the provider cannot be connected or synced locally, state that setup cannot use it as a shared workspace. Offer the local-only flow and explain that it will not synchronize automatically.

## Common storage rules

- Treat the existing customer-named Account folder as the source of truth. Do not recreate, rename, or move it.
- Confirm the local Account path before preparing the Opportunity.
- Keep user-reported storage access separate from connector authentication and local write readiness.
