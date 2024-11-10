# Buckystyle League Championship Series

## Overview

Buckystyle League Championship Series is a comprehensive system for managing, analyzing, and visualizing data related to the Buckystyle League. It includes data collection, processing, storage, visualization, prediction models, and a Discord bot for real-time updates.

## Project Structure

## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL
- Rust (for prediction models)
- Git

### Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/buckystyle_league.git
   cd buckystyle_league
   ```

2. **Install Poetry**

   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   export PATH="$HOME/.local/bin:$PATH"
   ```

3. **Initialize Poetry and Install Dependencies**

   ```bash
   poetry install
   ```

4. **Set Up Environment Variables**

   Create a `.env` file in the project root with the following variables:

   ```env
   TOKEN=your_ballchasing_api_token
   DATABASE_URL=postgresql://league_user:secure_password@localhost:5432/buckystyle_league
   DISCORD_BOT_TOKEN=your_discord_bot_token
   CHANNEL_ID=123456789012345678
   ```

5. **Initialize the Database**

   ```bash
   poetry run python database/init_db.py
   ```

6. **Run Data Collection and Processing Scripts**

   ```bash
   poetry run python scripts/data_collection.py
   poetry run python scripts/data_processing.py
   poetry run python scripts/generate_reports.py
   ```

7. **Run the Discord Bot**

   ```bash
   poetry run python discord_bot/bot.py
   ```

### Running Tests

```bash
poetry run python -m unittest discover tests
```
