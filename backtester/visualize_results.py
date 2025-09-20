import pandas as pd
import plotly.graph_objects as go
import os
import argparse

def generate_report(strategy_name: str):
    """
    Reads backtest results from a CSV file and generates an interactive
    HTML report with performance charts.
    """
    # --- 1. Load and Process Data ---
    script_dir = os.path.dirname(__file__)
    results_path = os.path.join(script_dir, 'backtest_results.csv')
    report_path = os.path.join(script_dir, 'backtest_report.html')

    if not os.path.exists(results_path):
        print(f"Error: Results file not found at {results_path}")
        return

    df = pd.read_csv(results_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date')
    df['cumulative_pnl'] = df['pnl'].cumsum()

    # --- 2. Generate Equity Curve Chart ---
    equity_curve = go.Figure()
    equity_curve.add_trace(go.Scatter(
        x=df['date'],
        y=df['cumulative_pnl'],
        mode='lines',
        name='Equity Curve',
        line=dict(color='blue', width=2)
    ))
    equity_curve.update_layout(
        title='Equity Curve - Cumulative Profit/Loss Over Time',
        xaxis_title='Date',
        yaxis_title='Cumulative PnL (INR)',
        template='plotly_white'
    )

    # --- 3. Generate Daily PnL Chart ---
    colors = ['green' if pnl > 0 else 'red' for pnl in df['pnl']]
    daily_pnl = go.Figure()
    daily_pnl.add_trace(go.Bar(
        x=df['date'],
        y=df['pnl'],
        name='Daily PnL',
        marker_color=colors
    ))
    daily_pnl.update_layout(
        title='Daily Profit & Loss',
        xaxis_title='Date',
        yaxis_title='PnL (INR)',
        template='plotly_white'
    )

    # --- 4. Calculate Summary Statistics ---
    total_pnl = df['cumulative_pnl'].iloc[-1]
    total_trades = len(df)
    winning_trades = df[df['pnl'] > 0].shape[0]
    losing_trades = df[df['pnl'] <= 0].shape[0]
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    avg_profit_per_trade = total_pnl / total_trades if total_trades > 0 else 0

    # --- 5. Assemble HTML Report ---
    # Get HTML for each chart
    equity_curve_html = equity_curve.to_html(full_html=False, include_plotlyjs='cdn')
    daily_pnl_html = daily_pnl.to_html(full_html=False, include_plotlyjs=False) # No need to include JS again

    html_content = f"""
    <html>
    <head>
        <title>Backtest Report: {strategy_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1, h2 {{ color: #333; }}
            .container {{ max-width: 1000px; margin: auto; }}
            .stats {{ display: flex; justify-content: space-around; background-color: #f7f7f7; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
            .stat-box {{ text-align: center; }}
            .stat-value {{ font-size: 24px; font-weight: bold; }}
            .stat-label {{ font-size: 14px; color: #666; }}
            .win {{ color: green; }}
            .loss {{ color: red; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Backtest Report: {strategy_name}</h1>

            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value {'win' if total_pnl > 0 else 'loss'}">{total_pnl:,.2f} INR</div>
                    <div class="stat-label">Total PnL</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{win_rate:.2f}%</div>
                    <div class="stat-label">Win Rate</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{total_trades}</div>
                    <div class="stat-label">Total Days Traded</div>
                </div>
                 <div class="stat-box">
                    <div class="stat-value {'win' if avg_profit_per_trade > 0 else 'loss'}">{avg_profit_per_trade:,.2f} INR</div>
                    <div class="stat-label">Avg. Profit / Day</div>
                </div>
            </div>

            <h2>Equity Curve</h2>
            {equity_curve_html}

            <h2>Daily PnL</h2>
            {daily_pnl_html}
        </div>
    </body>
    </html>
    """

    # --- 6. Write to File ---
    with open(report_path, 'w') as f:
        f.write(html_content)

    print(f"Successfully generated report: {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a visual backtest report.")
    parser.add_argument(
        "--strategy",
        type=str,
        default="9:27 Straddle",
        help="The name of the strategy to include in the report title."
    )
    args = parser.parse_args()

    generate_report(strategy_name=args.strategy)
