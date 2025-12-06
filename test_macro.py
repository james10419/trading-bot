from macro_intelligence import MacroIntelligence
import logging

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    m = MacroIntelligence()
    print("Fetching Macro Data...")
    data = m.fetch_macro_data()
    print("Macro Data:", data)
    
    print("\nFetching Technicals for Samsung Electronics...")
    tech = m.fetch_technical_indicators('005930.KS')
    if tech is not None:
        print(f"Price: {tech['Close']}")
        print(f"RSI: {tech['RSI']}")
    else:
        print("Failed to fetch technicals.")
