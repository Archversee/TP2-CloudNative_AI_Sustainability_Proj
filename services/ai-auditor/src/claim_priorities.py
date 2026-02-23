# CLAIM PRIORITIZATION STRATEGY

# High-priority claims that MUST be analyzed by AI (CRITICAL for ESG ratings)
HIGH_PRIORITY_CLAIMS = {
    # Core emissions (CRITICAL)
    "scope 1", "scope 1 emissions",
    "scope 2", "scope 2 emissions",
    "scope 3", "scope 3 emissions",
    "total emissions", "total GHG emissions",
    "GHG emissions", "greenhouse gas emissions",
    "carbon emissions", "CO2 emissions", "CO2e emissions",
    "direct emissions", "indirect emissions",
    
    # Net zero targets (CRITICAL)
    "net zero", "net-zero", "net zero by", "net zero emissions",
    "carbon neutral", "carbon neutrality", "carbon neutral by",
    "climate neutral",
    
    # Science-based targets (HIGH IMPORTANCE)
    "science-based targets", "SBTi", "SBT",
    "1.5°C target", "2°C target", "Paris Agreement",
    "science based target initiative",
    
    # Renewable energy (HIGH IMPORTANCE)
    "renewable energy", "renewable electricity", "renewable power",
    "clean energy", "solar energy", "wind energy",
}

# Medium-priority claims (include if space allows)
MEDIUM_PRIORITY_CLAIMS = {
    "emission reduction", "emissions intensity",
    "decarbonization", "decarbonisation",
    "carbon footprint",
    "energy consumption", "energy efficiency", "energy intensity",
    "water consumption", "water usage", "water withdrawal",
    "waste generated", "waste recycled", "waste to landfill",
    "circular economy", "recycling rate",
    "biodiversity", "deforestation", "reforestation",
    "green energy", "hydroelectric",
}

# Low-priority claims (extract but don't prioritize for AI)
LOW_PRIORITY_CLAIMS = {
    "employee safety", "health and safety", "lost time injury",
    "diversity and inclusion", "gender diversity",
    "human rights", "labor practices",
    "community engagement", "stakeholder engagement",
    "LEED certification", "green building", "B Corp",
    "ISO 14001", "ISO 50001",
    "GRI", "TCFD", "CDP", "SASB", "ISSB",
}