# Buckystyle League Championship Series

Table of Contents

    Workflow Overview
    Triggers
        Scheduled Trigger
        Manual Trigger
    Workflow Jobs and Steps
        1. Checkout Code
        2. Install Astral UV
        3. Setup Python
        4. Fetch and Process Data
        5. Send Images to Discord
        6. (Optional) Train Fantasy Points Model
    Workflow YAML Configuration
    Setup Instructions
    Notes
    License

Workflow Overview

The Daily Bot Task workflow is designed to perform the following automated tasks:

    Checkout the repository code.
    Set up the Python environment using Astral UV.
    Install necessary Python dependencies.
    Fetch and process data to create images and statistics.
    Send the generated images to a Discord channel.
    (Optional) Train a Fantasy Points model using Optuna.

Triggers

The workflow is triggered in two ways:

    Scheduled Trigger: Automatically runs every day at 1:00 AM UTC.
    Manual Trigger: Can be manually initiated through the GitHub Actions interface.

Scheduled Trigger

The workflow is scheduled to run daily at 1:00 AM UTC using a cron expression.

schedule:
  - cron: "0 1 * * *" # Runs daily at 1:00 AM UTC

    Note: The cron expression 0 1 * * * ensures the workflow runs at exactly 1:00 AM UTC every day.

Manual Trigger

You can manually trigger the workflow from the GitHub Actions tab in your repository.

workflow_dispatch: # Allows manual triggering if needed

Workflow Jobs and Steps
1. Checkout Code

Purpose: Clone the repository to the workflow runner.

- name: Checkout code
  uses: actions/checkout@v4

This step uses the actions/checkout action to clone your repository's code into the workflow environment.
2. Install Astral UV

Purpose: Set up the Astral UV environment with the specified Python version.

- name: Install astral uv
  uses: astral-sh/setup-uv@v4
  with:
    python-version: "3.11" # or your preferred version

This step installs Astral UV, a tool for managing Python environments, specifying Python version 3.11.
3. Setup Python

Purpose: Install Python dependencies using Astral UV.

- name: Setup python
  run: uv python install

This step runs the command to install Python dependencies as defined in your project using Astral UV.
4. Fetch and Process Data

Purpose: Execute the process.py script to fetch, filter data, and create images and statistics.

- name: Fetch data, filter data, and create images and stats
  env:
    TOKEN: ${{ secrets.TOKEN }}
    CHANNEL_ID3: ${{ secrets.CHANNEL_ID3 }}
    CURRENT_GROUP_ID: ${{ secrets.CURRENT_GROUP_ID }}
  run: |
    cd scripts
    uv run process.py

Environment Variables:

    TOKEN: Authentication token.
    CHANNEL_ID3: Discord channel ID.
    CURRENT_GROUP_ID: Current group identifier.

This step navigates to the scripts directory and runs the process.py script using Astral UV, utilizing necessary environment variables for authentication and configuration.
5. Send Images to Discord

Purpose: Execute the send_images.py script to send generated images to a Discord channel.

- name: Send images to discord channel
  env:
    DISCORD_TOKEN: ${{ secrets.DISCORD_TOKEN }}
    TOKEN: ${{ secrets.TOKEN }}
    CHANNEL_ID3: ${{ secrets.CHANNEL_ID3 }} # Use your Discord token secret here
  run: |
    cd discord_bot
    cd cogs
    uv run send_images.py

Environment Variables:

    DISCORD_TOKEN: Discord authentication token.
    TOKEN: Authentication token.
    CHANNEL_ID3: Discord channel ID.

This step navigates to the discord_bot/cogs directory and runs the send_images.py script using Astral UV to send the generated images to your specified Discord channel.
6. (Optional) Train Fantasy Points Model

Purpose: Train a Fantasy Points model using Optuna. This step is currently commented out and can be enabled if needed.

# - name: Train Fantasy points model with optuna
#   run: |
#     cd scripts
#     cd cogs
#     poetry run python -m predictions

To enable this step, remove the # symbols. This step navigates to the scripts/cogs directory and runs the predictions module using Poetry to train your Fantasy Points model with Optuna.
Workflow YAML Configuration

Below is the complete YAML configuration for the Daily Bot Task workflow:

name: Daily Bot Task

on:
  schedule:
    - cron: "0 1 * * *" # Runs daily at 1:00 AM UTC
  workflow_dispatch: # Allows manual triggering if needed

jobs:
  run-scripts:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install astral uv
        uses: astral-sh/setup-uv@v4
        with:
          python-version: "3.11" # or your preferred version

      - name: Setup python
        run: uv python install

      - name: Fetch data, filter data, and create images and stats
        env:
          TOKEN: ${{ secrets.TOKEN }}
          CHANNEL_ID3: ${{ secrets.CHANNEL_ID3 }}
          CURRENT_GROUP_ID: ${{ secrets.CURRENT_GROUP_ID }}
        run: |
          cd scripts
          uv run process.py

      # - name: Train Fantasy points model with optuna
      #   run: |
      #     cd scripts
      #     cd cogs
      #     poetry run python -m predictions

      - name: Send images to discord channel
        env:
          DISCORD_TOKEN: ${{ secrets.DISCORD_TOKEN }}
          TOKEN: ${{ secrets.TOKEN }}
          CHANNEL_ID3: ${{ secrets.CHANNEL_ID3 }} # Use your Discord token secret here
        run: |
          cd discord_bot
          cd cogs
          uv run send_images.py

Setup Instructions

    Clone the Repository

    git clone https://github.com/your-username/your-repo.git
    cd your-repo

    Configure Secrets

    Ensure that all the necessary secrets are configured in your GitHub repository settings. To add secrets:
        Navigate to your repository on GitHub.
        Go to Settings > Secrets and variables > Actions.
        Click on New repository secret and add the following secrets:
            TOKEN: Your authentication token.
            CHANNEL_ID3: Your Discord channel ID.
            CURRENT_GROUP_ID: Your current group identifier.
            DISCORD_TOKEN: Your Discord authentication token.

    Verify Directory Structure

    Ensure that the directory paths used in the workflow (scripts, discord_bot/cogs) match your project's actual directory structure.

    Modify Python Version (Optional)

    If your project requires a different Python version, update the python-version field in the workflow YAML accordingly.

    Enable Optional Steps (If Needed)

    If you want to enable the training of the Fantasy Points model, uncomment the relevant section in the workflow YAML by removing the # symbols.

Notes

    Astral UV Usage: The workflow utilizes Astral UV for environment setup and dependency management. Ensure it aligns with your project's requirements. If you're using a different tool for environment management, adjust the steps accordingly.

    Secrets Management: Keep your secrets secure. Do not expose them in your code or logs. GitHub Secrets are encrypted and only available to workflows.

    Manual Trigger: To manually trigger the workflow, navigate to the Actions tab in your repository, select the Daily Bot Task workflow, and click on the Run workflow button.

    Error Handling: Monitor the workflow runs in the Actions tab to ensure tasks are executing correctly. Review logs for troubleshooting if any step fails.

    Cron Timezone: The cron schedule uses UTC time. Adjust your schedule accordingly if you need it to run in a different timezone.
