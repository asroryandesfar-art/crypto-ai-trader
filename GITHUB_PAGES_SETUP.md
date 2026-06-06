# GitHub Pages Setup

The static judge demo is already contained in `docs/index.html` and requires no backend, QVAC process, secrets, or build step.

## Enable GitHub Pages

1. Open the repository: `https://github.com/asroryandesfar-art/crypto-ai-trader`.
2. Select **Settings**.
3. In the left sidebar, select **Pages** under **Code and automation**.
4. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
5. Select the `main` branch and the `/docs` folder.
6. Select **Save**.
7. Wait for GitHub Pages to finish its first deployment.

## Expected URL

```text
https://asroryandesfar-art.github.io/crypto-ai-trader/
```

The first publication can take several minutes. Confirm that the page loads in a private browser window after GitHub reports a successful deployment.

## Update DoraHacks

1. Open the Crypto AI Trader QVAC project in the DoraHacks builder dashboard.
2. Edit the project or submission details.
3. Set the **Project Website** field to:

   `https://asroryandesfar-art.github.io/crypto-ai-trader/`

4. Keep the GitHub repository field pointed to:

   `https://github.com/asroryandesfar-art/crypto-ai-trader`

5. Save the project and open the public submission page to verify both links.

## Publish Updates

Changes pushed to `main` under `docs/` are redeployed automatically. Check the repository's **Actions** or **Settings > Pages** screen if an update does not appear.
