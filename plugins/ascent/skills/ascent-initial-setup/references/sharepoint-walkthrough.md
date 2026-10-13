# SharePoint Walkthrough

Use this reference only when the user selects SharePoint storage.

## Locate or create the Account folder

Use `ASCENT_SHAREPOINT_ACCOUNTS_URL` as the Account-folder URL when it is configured. Otherwise use this default:

```text
https://twodegrees1.sharepoint.com/teams/Ascent/Shared%20Documents/Forms/AllItems.aspx?id=%2Fteams%2FAscent%2FShared%20Documents%2FAccounts&viewid=0a588853%2D4cd8%2D489c%2Db39e%2Dd322bfb46652
```

Send, **"Here is a link to the Ascent Account Folder. Look to see if the account already exists."** Render **Ascent Account Folder** as linked text using the resolved Account-folder URL.

Ask, **"Did you find a folder for the account you are working on?"** Offer short choices for **Yes, I found it** and **No, it is missing**.

If the Account folder is missing, send these steps:

> 1. Click the **+ Create or upload** button.
> 2. Select **Folder**.
> 3. Type the Account name in the **Name** field.
> 4. Click the **Create** button.

Immediately below the steps, display these images in order with absolute filesystem paths:

1. [The Create or upload example](../assets/sharepoint-create-or-upload.png), with alt text naming the highlighted button.
2. [The Folder option example](../assets/sharepoint-select-folder.png), with alt text naming the highlighted option.
3. [The Create a folder example](../assets/sharepoint-create-account-folder.png), with alt text naming the field and highlighted button.

Mark this setup as a new Project. Continue directly to the shortcut steps.

## Add the OneDrive shortcut

When the Account folder exists, send:

> 1. Navigate to the Account folder by clicking it.
> 2. Click the **Add shortcut to OneDrive** button.
> 3. Select **My files** from the menu that opens.

Immediately below the steps, display these images in order with absolute filesystem paths:

1. [The SharePoint shortcut example](../assets/sharepoint-add-shortcut-to-onedrive.png), with alt text naming the highlighted button.
2. [The My files example](../assets/sharepoint-select-my-files.png), with alt text naming the highlighted option.

Then say:

> Once you have clicked on "My Files" let me know the name of the account and I will go look for the local connection to that folder you just created

Stop and wait for the Account name. Do not also request the synced path or Edit-access confirmation.

## Resolve the local connection

After receiving the Account name, inspect standard local OneDrive sync locations. Search first for `Ascent - <Account name>`, then `<Account name>`. Compare case-insensitively, require exact names, and resolve candidates before presenting them.

- With one valid match, report it and continue.
- With no match, explain that syncing may still be in progress and offer to retry. As a fallback, tell the user to select the Account folder in Finder, hold **Option**, right-click, choose **Copy "<Account name>" as Pathname**, and paste the path.
- With multiple matches, describe them and ask the user to choose. Do not guess.

Use the SharePoint connector to resolve site, library, and folder metadata when available, but do not read file contents during setup. Connector access cannot establish OneDrive synchronization. Confirm user-reported Edit access separately after resolving the local path, and do not claim to have inspected permissions.

Continue only after confirming the locally synced Account path. Do not use an ordinary downloaded copy as the working location.
