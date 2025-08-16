# APT Token Economy Simulation Dashboard

This project is a **Streamlit-powered dashboard** for simulating the APT token economy under a solar infrastructure revenue model. It combines **financial modeling**, **staking mechanics**, and **token burn dynamics** into an interactive interface with customizable parameters.

---

## Features

* **Interactive Controls (Sidebar):**

  * Toggle between *Manual* and *Yield-Based* staking modes.
  * Adjust investor allocation %, staking duration, and staking percentages.
* **Token Economics Simulation:**

  * Tracks supply, staking, burns, and price evolution over 48 months.
  * Includes deflator mechanics, revenue-based buybacks, and token burns.
* **Revenue Modeling:**

  * Simulates solar power deployment over 10 months.
  * Calculates monthly and annual revenue from electricity sales.
* **Dynamic Visualizations:**

  * Token price, FDV, and market cap trends.
  * Circulating supply, staked tokens, and staking yield.
  * Token burn progression and revenue growth.
* **Summary Statistics:**

  * Final token price, appreciation %, total revenue, cumulative burns.
  * Solar infrastructure capacity and generation metrics.
  * Breakdown of token allocations.

---

## Tech Stack

* **Python**
* [Streamlit](https://streamlit.io) – interactive UI
* [Plotly](https://plotly.com/python/) – charts and subplots
* **Pandas / NumPy** – data simulation and calculations

---

## How to Run

1. Clone this repository.
2. Install dependencies:

   ```bash
   pip install streamlit pandas numpy plotly
   ```
3. Run the dashboard:

   ```bash
   streamlit run app.py
   ```
4. Open the local URL shown in your terminal to interact with the simulation.

---

## Notes

* Total supply is fixed at **100M APT**.
* Funding assumption: **\$10M raised** for solar deployment.
* Economic flows model investor allocations, staking rewards, token burns, and AMM-based buybacks.
* Simulation results are **hypothetical** and should not be treated as financial advice.

