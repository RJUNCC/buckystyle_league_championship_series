# Buckystyle League Championship Series

# Daily Bot Task Workflow

This repository includes a **Daily Bot Task** GitHub Actions workflow designed to automate the execution of various bot-related tasks. The workflow is scheduled to run daily at 1:00 AM UTC and can also be triggered manually when needed.

## Table of Contents

- [Workflow Overview](#workflow-overview)
- [Triggers](#triggers)
  - [Scheduled Trigger](#scheduled-trigger)
  - [Manual Trigger](#manual-trigger)
- [Workflow Jobs and Steps](#workflow-jobs-and-steps)
  - [1. Checkout Code](#1-checkout-code)
  - [2. Install Astral UV](#2-install-astral-uv)
  - [3. Setup Python](#3-setup-python)
  - [4. Fetch and Process Data](#4-fetch-and-process-data)
  - [5. Send Images to Discord](#5-send-images-to-discord)
  - [6. (Optional) Train Fantasy Points Model](#6-optional-train-fantasy-points-model)
- [Workflow YAML Configuration](#workflow-yaml-configuration)
- [Setup Instructions](#setup-instructions)
- [Notes](#notes)
- [License](#license)

## Workflow Overview

The **Daily Bot Task** workflow is designed to perform the following automated tasks:

1. **Checkout the repository code.**
2. **Set up the Python environment using Astral UV.**
3. **Install necessary Python dependencies.**
4. **Fetch and process data to create images and statistics.**
5. **Send the generated images to a Discord channel.**
6. **(Optional) Train a Fantasy Points model using Optuna.**

## Triggers

The workflow is triggered in two ways:

- **Scheduled Trigger:** Automatically runs every day at 1:00 AM UTC.
- **Manual Trigger:** Can be manually initiated through the GitHub Actions interface.

### Scheduled Trigger

The workflow is scheduled to run daily at 1:00 AM UTC using a cron expression.

```yaml
schedule:
  - cron: "0 1 * * *" # Runs daily at 1:00 AM UTC
