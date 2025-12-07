"""
Production-Quality Script to Populate 1000+ Companies with REAL Events

This script:
1. Uses hardcoded but current S&P 500 tickers + biotech/tech companies (1000+ total)
2. Adds all companies to the database using DataManager
3. Runs actual scanners to fetch REAL events from official sources
4. Each scanner saves events using DataManager.add_event() directly
5. Robust error handling and progress logging throughout

Usage:
    python backend/scripts/populate_1000_companies.py [--skip-companies] [--skip-events] [--batch-size 50]
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import argparse
import time
from typing import List, Dict, Optional
from loguru import logger

# Import DataManager
from data_manager import DataManager

# Import all scanner implementations
from scanners.impl.sec_8k import scan_sec_8k
from scanners.impl.sec_10q import scan_sec_10q
from scanners.impl.earnings import scan_earnings_calls
from scanners.impl.fda import scan_fda
from scanners.impl.guidance import scan_guidance
from scanners.impl.ma import scan_ma
from scanners.impl.dividend import scan_dividend_buyback
from scanners.impl.product_launch import scan_product_launch
from scanners.impl.press import scan_press


# ============================================================================
# HARDCODED S&P 500 TICKERS (Current as of Nov 2025)
# ============================================================================

SP500_TICKERS = [
    # Tech & Communication Services
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL",
    "ADBE", "CRM", "CSCO", "ACN", "AMD", "INTC", "IBM", "QCOM", "INTU", "NOW",
    "AMAT", "ADI", "LRCX", "KLAC", "SNPS", "CDNS", "MCHP", "NXPI", "FTNT", "ANSS",
    "TXN", "MU", "PANW", "ADSK", "ROP", "PLTR", "WDAY", "TEAM", "DDOG", "SNOW",
    "ZS", "NET", "CRWD", "ABNB", "UBER", "LYFT", "DASH", "COIN", "RBLX", "U",
    
    # Healthcare & Pharma
    "UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "ABT", "DHR", "PFE", "AMGN",
    "BMY", "GILD", "CVS", "CI", "ELV", "HCA", "ISRG", "VRTX", "REGN", "ZTS",
    "MRNA", "MCK", "COR", "IDXX", "IQV", "A", "DGX", "BDX", "SYK", "BSX",
    "EW", "RMD", "HOLX", "MTD", "BAX", "WAT", "ALGN", "DXCM", "PODD", "INCY",
    "BIIB", "TECH", "VTRS", "XRAY", "HUM", "CNC", "MOH", "UHS", "DVA", "ENOV",
    
    # Financials
    "BRK.B", "V", "MA", "JPM", "BAC", "WFC", "GS", "MS", "AXP", "SCHW",
    "BLK", "SPGI", "C", "PGR", "CB", "MMC", "AON", "ICE", "CME", "MCO",
    "PNC", "USB", "TFC", "COF", "AIG", "MET", "PRU", "AFL", "ALL", "TRV",
    "FITB", "HBAN", "RF", "CFG", "KEY", "WTW", "BRO", "MKTX", "NDAQ", "CBOE",
    
    # Consumer Discretionary & Retail
    "AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW", "TJX", "BKNG", "ABNB",
    "CMG", "ORLY", "MAR", "GM", "F", "HLT", "YUM", "DPZ", "ROST", "LULU",
    "AZO", "ULTA", "DG", "DLTR", "EBAY", "ETSY", "W", "CHWY", "CVNA", "KMX",
    
    # Consumer Staples
    "WMT", "PG", "COST", "KO", "PEP", "PM", "MO", "MDLZ", "CL", "KMB",
    "GIS", "K", "HSY", "SJM", "CAG", "CPB", "CHD", "CLX", "TSN", "HRL",
    
    # Industrials
    "HON", "UNP", "RTX", "UPS", "CAT", "BA", "GE", "LMT", "DE", "MMM",
    "ETN", "NOC", "ITW", "EMR", "GD", "CSX", "NSC", "FDX", "PCAR", "CMI",
    "PH", "ROK", "AME", "FAST", "ODFL", "VRSK", "PAYX", "IEX", "DOV", "XYL",
    
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL",
    "DVN", "FANG", "BKR", "HES", "MRO", "APA", "CTRA", "EQT", "OVV", "PR",
    
    # Materials
    "LIN", "APD", "SHW", "ECL", "DD", "NEM", "FCX", "NUE", "DOW", "PPG",
    "ALB", "VMC", "MLM", "IFF", "FMC", "CE", "BALL", "AVY", "PKG", "IP",
    
    # Utilities
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "PEG", "XEL", "ED",
    "ES", "WEC", "DTE", "EIX", "ETR", "FE", "PPL", "AEE", "CMS", "CNP",
    
    # Real Estate
    "PLD", "AMT", "EQIX", "PSA", "WELL", "DLR", "SPG", "O", "VICI", "AVB",
    "EQR", "INVH", "VTR", "ARE", "MAA", "ESS", "UDR", "CPT", "KIM", "REG",
]

# ============================================================================
# BIOTECH & TECH SMALL/MID CAPS (to reach 1000+)
# ============================================================================

BIOTECH_TECH_TICKERS = [
    # Biotech Small/Mid Caps with Active FDA Pipelines
    "ACAD", "ALNY", "ALPN", "ARDX", "ARWR", "ARVN", "AXSM", "BCRX", "BGNE",
    "BLUE", "BPMC", "CARA", "CLDX", "CORT", "CRBP", "CRIS", "CRSP", "CRTX",
    "CVAC", "DNLI", "DRNA", "DVAX", "EDIT", "ETNB", "FATE", "FDMT", "FOLD",
    "GTHX", "HCAT", "HOOK", "HROW", "IBRX", "IDYA", "IGMS", "IMAB", "IMNM",
    "IMTX", "IPSC", "IRWD", "ITCI", "JNCE", "KALA", "KALV", "KPTI", "KRYS",
    "KYMR", "LCTX", "LEGN", "LENZ", "LMNR", "LOGC", "LPTX", "LYEL", "MDGL",
    "MGNX", "MIRM", "MRTX", "MRUS", "MRVI", "NTLA", "NVAX", "OCUL", "PGEN",
    "PRTA", "PRTK", "PTCT", "PTGX", "PRVB", "REPL", "RGNX", "ROIV", "RXRX",
    "SAGE", "SAVA", "SDGR", "SGMO", "SNDX", "SUPN", "TGTX", "VBIV", "VCEL",
    "VKTX", "VRDN", "VYGR", "XLRN", "YMAB", "ZLAB", "ZNTL", "ZYME", "AGIO",
    "ALLO", "ABUS", "APLS", "ATNM", "AUTL", "AVXL", "BEAM", "BPTH", "CMPS",
    "CYTK", "DMTK", "ESPR", "EXEL", "FGEN", "GLPG", "HALO", "IONS", "KROS",
    "LXRX", "MNKD", "NBIX", "NKTR", "NVCR", "OPCH", "PBYI", "PCRX", "RARE",
    "RLAY", "RVMD", "SGEN", "SRPT", "STOK", "TBPH", "TYME", "VCYT", "VRTX",
    
    # Tech Small/Mid Caps
    "ACIW", "AFRM", "ALRM", "AMBA", "APPN", "ASAN", "AVID", "BAND", "BOX",
    "CALX", "CDAY", "CEVA", "CFLT", "CLVT", "CVLT", "CVNA", "CYBR", "DAKT",
    "DOCN", "DOMO", "ENSG", "FIVN", "FROG", "GTLB", "IOT", "JAMF", "NCNO",
    "NEWR", "NTNX", "PATH", "PCTY", "PD", "QLYS", "RPD", "S", "SAIL", "SMAR",
    "SPSC", "TENB", "VEEV", "VRNS", "ZI", "ZUO", "AI", "BILL", "CFLT", "COUP",
    "ESTC", "FSLY", "HUBS", "MDB", "OKTA", "PLAN", "ROKU", "SQ", "TWLO", "ZM",
    
    # Industrial Small/Mid Caps
    "AIT", "ATKR", "BOOM", "CSWI", "ENS", "ESAB", "ERII", "FSS", "GTLS",
    "HSII", "LECO", "MANT", "MLI", "MATW", "NP", "NPO", "PRIM", "RBC",
    "RXO", "SLGN", "SXI", "TPC", "TRN", "TRS", "VSM", "WERN",
    
    # Healthcare Small/Mid Caps
    "ACHC", "ADMA", "ALHC", "AMN", "CRVL", "ENSG", "EVH", "GMED", "HIMS",
    "KNSA", "LMAT", "OMCL", "PDCO", "PNTG", "PRVA", "RDNT", "SGRY", "TMDX",
    
    # Retail/Consumer Small/Mid Caps
    "BOOT", "CBRL", "CASY", "CHDN", "DNUT", "FIVE", "GRBK", "HIBB", "LE",
    "MNRO", "OLLI", "PLCE", "PRDO", "SAH", "TXRH", "UPBD", "WINA",
    
    # Additional High-Quality Mid Caps
    "ANET", "FICO", "MPWR", "MRVL", "ON", "SWKS", "WOLF", "CRUS", "SLAB", "ALGM",
    "ENTG", "MKSI", "ONTO", "PLAB", "DIOD", "LITE", "MACOM", "NVEC",
    "POWI", "SMTC", "STRS", "TQNT", "UTHR", "VIAV", "ATEN", "FORM", "WDC",
    
    # Additional NASDAQ-100 and Russell 2000 Companies (400+ more to reach 1000+)
    "AAL", "AMAT", "ATVI", "ADSK", "ADP", "AZN", "BIDU", "BKNG", "CDNS", "CHTR",
    "CMCSA", "COST", "CPRT", "CTAS", "DXCM", "EA", "EBAY", "EXC", "FAST", "FISV",
    "FOX", "FOXA", "GFS", "ILMN", "INCY", "ISRG", "JD", "LRCX", "LULU", "MAR",
    "MCHP", "MDLZ", "MNST", "MRNA", "MRVL", "MTCH", "NFLX", "NXPI", "ODFL", "ORLY",
    "PAYX", "PCAR", "PYPL", "REGN", "ROST", "SBAC", "SGEN", "SIRI", "SPLK", "SWKS",
    "TCOM", "TMUS", "TSLA", "TXN", "VRSN", "VRSK", "VRTX", "WBA", "WDAY", "XEL",
    "ZM", "ZS", "AFRM", "ALLY", "BILL", "BROS", "CART", "CAVA", "CELH", "CERT",
    "CLOV", "COKE", "COUR", "CPNG", "CROX", "DKNG", "DUOL", "EVGO", "FIGS", "FRPT",
    "FTCI", "FWONA", "FWONK", "HOOD", "KTOS", "LCID", "LMND", "LPLA", "LUMO", "LYFT",
    "MTTR", "NU", "OLLI", "OPEN", "PINS", "RIVN", "RVLV", "SE", "SHOP", "SKLZ",
    "SNAP", "SOFI", "SPOT", "SYM", "TALK", "TDUP", "UPST", "UWMC", "VIPS", "WISH",
    "XPEV", "YETI", "ZG", "ZION",
    
    # Additional Biotech (Small/Mid Cap)
    "ABCL", "ABUS", "ACRS", "ADAP", "ADCT", "ADVM", "AGLE", "AKBA", "AKRO", "ALBO",
    "ALEC", "ALLO", "ALXO", "AMRN", "AMRS", "ANAB", "ANIP", "APLS", "APRE", "AQST",
    "ARAY", "ARCT", "ARQT", "ARTL", "ARVN", "ASND", "ATNM", "ATRC", "ATNX", "ATXS",
    "AUPH", "AUTL", "AVEO", "AVID", "AVIR", "AVXL", "AXNX", "AYLA", "BCAB", "BEAM",
    "BCRX", "BDTX", "BFRI", "BHVN", "BIOL", "BIVI", "BLDP", "BLFS", "BNTX", "BOLD",
    "BPMC", "BPRN", "BPTH", "BTAI", "CADL", "CALB", "CARA", "CAPR", "CART", "CASI",
    "CBAY", "CBIO", "CCCC", "CERE", "CERS", "CGEM", "CGEN", "CHRS", "CLDX", "CLNN",
    "CLPT", "CLSD", "CLVS", "CMPS", "CNST", "COCP", "COGT", "COHN", "COLL", "CORT",
    "COYA", "CRBU", "CRBP", "CRIS", "CRMD", "CRNX", "CRSP", "CRTX", "CSMD", "CSTL",
    "CTKB", "CTMX", "CTRE", "CTIC", "CTSO", "CTTC", "CTUR", "CYTK", "CYTO", "DARE",
    "DAWN", "DBVT", "DERM", "DFFN", "DMTK", "DNLI", "DRMA", "DRNA", "DRRX", "DSCO",
    "DSGX", "DTHD", "DVAX", "DYNE", "DZNE", "EARS", "ECOR", "EDAP", "EDIT", "EDSA",
    "EFTR", "EGAN", "EGLE", "EIGR", "ELTX", "ENTA", "ENTX", "EOLS", "EPIX", "EPRX",
    "ERAS", "ERII", "ESPR", "ETNB", "ETRN", "EVAX", "EVGN", "EVLO", "EVOK", "EXAS",
    "EXEL", "EXPI", "EYE", "FATE", "FBIO", "FDMT", "FENC", "FGEN", "FIXX", "FLDM",
    "FLGT", "FLNT", "FOLD", "FONR", "FORK", "FREQ", "FULC", "FVCB", "FXNC", "GAIN",
    "GANX", "GATO", "GBIO", "GCBC", "GENE", "GERN", "GEST", "GLMD", "GLNG", "GLPG",
    "GLUE", "GOSS", "GPCR", "GPRE", "GTHX", "GUTS", "HALO", "HARP", "HCAT", "HCSG",
    "HDNG", "HEAR", "HIMS", "HMNF", "HMST", "HOOK", "HOWL", "HROW", "HRTX", "HSTO",
    "HUMA", "HWKN", "IART", "IBCP", "IBEX", "IBIO", "IBRX", "ICAD", "ICLR", "ICUI",
    "IDEX", "IDYA", "IGIC", "IGMS", "IHRT", "IIVI", "IKNX", "ILPT", "IMAB", "IMAC",
    "IMAQ", "IMDZ", "IMGN", "IMNM", "IMNN", "IMRA", "IMRX", "IMTX", "IMUX", "IMVT",
    "INAB", "INBK", "INDP", "INDT", "INFU", "INGN", "INKT", "INMD", "INNT", "INSM",
    "INVA", "INVE", "IONS", "IOSP", "IOVA", "IPSC", "IRIX", "IRMD", "IRTC", "IRWD",
    "ISEE", "ISPC", "ITCI", "ITI", "ITRN", "IVAC", "IXHL", "JNCE", "KALV", "KALA",
    "KBLM", "KDNY", "KFFB", "KMBR", "KMPH", "KNDI", "KNSA", "KNTE", "KPTI", "KRKR",
    "KRON", "KROS", "KRTX", "KRYS", "KTCC", "KTRA", "KURA", "KYMR", "LCTX", "LEGN",
    "LENZ", "LEXO", "LFMD", "LFLY", "LHDX", "LIFE", "LIVN", "LMNR", "LNSR", "LNTH",
    "LOGC", "LPTX", "LQDA", "LQDT", "LRCX", "LTRN", "LUNA", "LVTX", "LXRX", "LYEL",
    "LYFT", "LYRA", "LYTX", "MBIN", "MCRB", "MDGL", "MDGS", "MDNA", "MDVL", "MDWD",
    "MDXG", "MDXH", "MEGL", "MEIP", "MESO", "MGTX", "MGNX", "MGRC", "MGYR", "MHLD",
    "MIRM", "MLYS", "MNKD", "MNOV", "MNPR", "MNRL", "MNRO", "MNSB", "MOLN", "MORF",
    "MOXC", "MRCY", "MREO", "MRNA", "MRNS", "MRTX", "MRUS", "MRVI", "MRVL", "MSBI",
    "MTEM", "MTEX", "MTLS", "MTRX", "MVBF", "MYGN", "MYOV", "NAOV", "NARI", "NATH",
    "NAVI", "NAVB", "NBIX", "NBRV", "NCNA", "NCSM", "NEPH", "NESR", "NETE", "NEWS",
    "NFBK", "NKTR", "NKTX", "NLSP", "NMIH", "NMTR", "NNBR", "NNVC", "NOTV", "NOVN",
    "NRIX", "NSIT", "NSTG", "NTLA", "NTRA", "NUVA", "NVAX", "NVFY", "NVRO", "NVTS",
    "NWBI", "NWGL", "NWPX", "NXGN", "NXRT", "NXST", "OABI", "OAKK", "OBLG", "OBSV",
    "OCFC", "OCGN", "OCUL", "ODFL", "OFIX", "OFLX", "OFS", "OILD", "OIIM", "OKCMF",
    "OKTA", "OLED", "OLLI", "OMAB", "OMER", "OMEX", "ONDS", "ONMD", "ONVO", "OOMA",
    "OPBK", "OPCH", "OPFI", "OPGN", "OPRT", "OPTN", "ORGO", "ORMP", "OSBC", "OSBK",
    "OSCR", "OSMT", "OSIS", "OSPR", "OSUR", "OTEC", "OTRK", "OVID", "OVLY", "OXBR",
    "PACB", "PASG", "PBFS", "PBHC", "PBIP", "PBTS", "PCSA", "PCTY", "PCVX", "PDCO",
    "PDEX", "PDFS", "PDLB", "PDLI", "PDSB", "PEBO", "PECO", "PEGA", "PEIX", "PGEN",
    "PGNY", "PHAS", "PHIO", "PHUN", "PHVS", "PIII", "PINC", "PIRS", "PLAB", "PLAG",
    "PLAY", "PLBC", "PLCE", "PLIN", "PLRX", "PLSE", "PLXP", "PLYA", "PLYM", "PMVP",
    "PNBK", "PNFP", "PNTG", "POHC", "POLA", "POOL", "PODD", "PRAA", "PRAX", "PRCH",
    "PRDO", "PRFT", "PRGS", "PRIM", "PRPH", "PRPL", "PRQR", "PRSO", "PRST", "PRVA",
    "PRVB", "PSTV", "PSTX", "PTCT", "PTEN", "PTIN", "PTIX", "PTNR", "PTRA", "PTSI",
    "PULM", "PUMP", "PVAC", "PXLW", "PYCR", "PYPD", "QDEL", "QNRX", "QRHC", "QRTEA",
    "QRTEB", "QTNT", "QTTB", "QUOT", "QURE", "RARE", "RBBN", "RBCAA", "RBNC", "RBOT",
    "RCEL", "RCKT", "RCKY", "RCMT", "RCON", "RDCM", "RDFN", "RDHL", "RDIB", "RDNT",
    "RDUS", "RDVT", "RDWR", "REAL", "REAX", "RECV", "REED", "REFR", "REGN", "REKR",
    "RELL", "RELX", "RENB", "REPH", "REPL", "REYN", "RFIL", "RGCO", "RGEN", "RGNX",
    "RIBT", "RICK", "RIGL", "RILY", "RILYG", "RLMD", "RMBL", "RMBS", "RMCF", "RMGN",
    "RMNI", "RMTI", "RNAC", "RNEM", "RNET", "RNLX", "ROAD", "ROCC", "ROCK", "ROIV",
    "ROLL", "ROSE", "ROST", "RPAY", "RPRX", "RPTX", "RRBI", "RRGB", "RRR", "RSLS",
    "RSSS", "RTLR", "RTRX", "RUBY", "RUBI", "RUHN", "RUN", "RUSHA", "RUSHB", "RUTH",
    "RVMD", "RVNC", "RVPH", "RVSB", "RWLK", "RXDX", "RXRA", "RXRX", "RYAAY", "RYTM",
    "SAGE", "SAIA", "SAKS", "SALM", "SAML", "SAMG", "SANM", "SANW", "SASR", "SATS",
    "SAVA", "SBCF", "SBFG", "SBGI", "SBLK", "SBOT", "SBPH", "SBSI", "SBUX", "SCHN",
    "SCKT", "SCLX", "SCOR", "SCPH", "SCPS", "SCRM", "SCSC", "SCVL", "SCWX", "SCYX",
    "SDGR", "SEAC", "SEAS", "SECO", "SELF", "SENEA", "SENEB", "SENS", "SFIX", "SFNC",
    "SFST", "SGBX", "SGDM", "SGEN", "SGFY", "SGHT", "SGMA", "SGMO", "SGMS", "SGRP",
    "SGRY", "SHAK", "SHBI", "SHEN", "SHFS", "SHIP", "SHLS", "SHOO", "SHOP", "SHSP",
    "SHO", "SIBN", "SIEB", "SIEN", "SIGA", "SIGI", "SILC", "SILK", "SIMO", "SINT",
    "SIRO", "SITM", "SKIL", "SKIN", "SKYW", "SKYX", "SKYY", "SLAB", "SLCT", "SLDB",
    "SLDP", "SLGC", "SLGL", "SLHG", "SLMBP", "SLNG", "SLNH", "SLNO", "SLP", "SLQT",
    "SLRC", "SMBC", "SMBK", "SMCI", "SMED", "SMFL", "SMID", "SMLR", "SMMT", "SMPL",
    "SMRT", "SMSI", "SMTC", "SMWB", "SNAP", "SNAX", "SNBR", "SNCA", "SNCR", "SNCY",
    "SNDL", "SNDX", "SNEX", "SNFCA", "SNGX", "SNOA", "SNPS", "SNPX", "SNSE", "SNTI",
    "SOFI", "SOFO", "SOHU", "SOLO", "SOLY", "SONN", "SONX", "SOPA", "SOPH", "SPFI",
    "SPGC", "SPHD", "SPHS", "SPKE", "SPLP", "SPNE", "SPNS", "SPOK", "SPRC", "SPRO",
    "SPSC", "SPT", "SPTN", "SPWH", "SPWR", "SQFT", "SQQQ", "SRAX", "SRCE", "SRCL",
    "SRDX", "SRET", "SRGA", "SRI", "SRNL", "SRPT", "SRRK", "SRTS", "SSB", "SSBI",
    "SSBK", "SSIC", "SSKN", "SSNC", "SSNT", "SSRM", "SSSS", "SSTK", "SSYS", "STAA",
    "STAF", "STAR", "STBA", "STCN", "STFC", "STIM", "STKL", "STKS", "STLD", "STMP",
    "STNE", "STNG", "STOK", "STRA", "STRL", "STRO", "STRR", "STRS", "STRT", "STSA",
    "STSS", "STXS", "SUPN", "SURF", "SURG", "SUSB", "SUSC", "SUSL", "SUSP", "SVA",
    "SVBI", "SVBK", "SVFD", "SVII", "SVM", "SVMK", "SVRA", "SVVC", "SWAG", "SWBI",
    "SWIR", "SWKS", "SWTX", "SYBX", "SYKE", "SYLD", "SYNH", "SYNL", "SYPR", "SYRS",
    "SYTA", "TACT", "TAIT", "TALS", "TANNI", "TANNL", "TANNZ", "TAOP", "TARA", "TARO",
    "TAYD", "TBBK", "TBIO", "TBPH", "TCBC", "TCBI", "TCBK", "TCBX", "TCCO", "TCDA",
    "TCFC", "TCMD", "TCOM", "TCON", "TCPC", "TCVA", "TDUP", "TEAM", "TECH", "TELA",
    "TELL", "TENB", "TENX", "TERN", "TESS", "TFII", "TFIN", "TFSL", "TGLS", "TGNA",
    "TGTX", "THFF", "THMO", "THRM", "THRY", "THTX", "THWWW", "TIGO", "TIGR", "TINE",
    "TISI", "TITN", "TIVC", "TKAT", "TKHNY", "TLGT", "TLMD", "TLPH", "TLRY", "TLSA",
    "TLYS", "TMDX", "TMDI", "TMHC", "TMUS", "TNAV", "TNDM", "TNON", "TNXP", "TOKE",
    "TOPS", "TORC", "TOUR", "TOWN", "TPCS", "TPGH", "TPHS", "TPIC", "TPRE", "TPTX",
    "TQQQ", "TRDA", "TREE", "TRHC", "TRIB", "TRIL", "TRIN", "TRIP", "TRMB", "TRMD",
    "TRMK", "TRMR", "TRMT", "TRNS", "TRNX", "TROW", "TROX", "TRST", "TRUE", "TRUP",
    "TRVG", "TRVN", "TRVI", "TSBK", "TSBX", "TSEM", "TSHA", "TSLA", "TSLX", "TSP",
    "TSRI", "TTCF", "TTD", "TTEC", "TTEK", "TTGT", "TTMI", "TTOO", "TTSH", "TTWO",
    "TUSK", "TVTX", "TW", "TWKS", "TWLO", "TWLV", "TWND", "TWOU", "TWST", "TXMD",
    "TXRH", "TYME", "TZOO", "UAMY", "UBCP", "UBER", "UBFO", "UBOH", "UBSI", "UCBI",
    "UCFC", "UCTT", "UEIC", "UEPS", "UFAB", "UFCS", "UFI", "UFPI", "UFPT", "UG",
    "UGRO", "UHAL", "UHALB", "UHG", "UIHC", "ULBI", "ULH", "ULTA", "ULTI", "UMBF",
    "UMPQ", "UNAM", "UNCY", "UNF", "UNFI", "UNIT", "UNTY", "UONE", "UONEK", "UPBD",
    "UPC", "UPLD", "UPST", "UPWK", "URBN", "URGN", "UROY", "USAK", "USAP", "USAU",
    "USEG", "USFR", "USIO", "USLM", "USNA", "USWS", "UTHR", "UTRS", "UTSI", "UWMC",
    "UXIN", "VACC", "VANI", "VAPO", "VCEL", "VCNX", "VCTR", "VCYT", "VECO", "VEEV",
    "VEON", "VERA", "VERB", "VERI", "VERO", "VERU", "VERX", "VERY", "VERU", "VET",
    "VETS", "VEV", "VFF", "VG", "VGR", "VGSH", "VGSI", "VIAV", "VICI", "VICR",
    "VIEW", "VIOT", "VIPS", "VIR", "VIRI", "VIRT", "VISL", "VITL", "VIVK", "VIVO",
    "VKTX", "VLAY", "VLCN", "VLGEA", "VLN", "VLRS", "VLTA", "VLVLY", "VMEO", "VNET",
    "VNLA", "VNOM", "VNTR", "VONE", "VONG", "VONV", "VOOV", "VOOT", "VORBF", "VOXR",
    "VOXX", "VPCC", "VQS", "VRCA", "VRDN", "VREX", "VRM", "VRME", "VRMEF", "VRNA",
    "VRNS", "VRNT", "VRRM", "VRSK", "VRSN", "VRTS", "VRTV", "VRTX", "VSAT", "VSEC",
    "VSTA", "VSTM", "VSTO", "VTAQ", "VTEX", "VTGN", "VTHR", "VTIQ", "VTNR", "VTRS",
    "VTRU", "VTSI", "VTVT", "VTWG", "VTWV", "VUZI", "VVPR", "VVUS", "VXRT", "VYGR",
    "VYNE", "WABC", "WAFD", "WAFU", "WASH", "WATT", "WB", "WBA", "WBND", "WBTN",
    "WBX", "WCFB", "WD", "WDAY", "WDFC", "WEBK", "WEBL", "WEJO", "WELL", "WERN",
    "WETG", "WEYS", "WFCF", "WGO", "WHLM", "WHLR", "WHLRD", "WHR", "WIFI", "WILC",
    "WIMI", "WINA", "WING", "WINT", "WIRE", "WISA", "WISH", "WIX", "WKEY", "WLDN",
    "WLFC", "WLKP", "WLL", "WLTW", "WLY", "WMGI", "WMK", "WNEB", "WNW", "WORX",
    "WRBY", "WRLD", "WSBC", "WSBF", "WSFS", "WSG", "WSTG", "WTBA", "WTER", "WTFC",
    "WTFCM", "WTFCP", "WTI", "WTMA", "WTO", "WTRE", "WTRG", "WTRH", "WTS", "WVE",
    "WVFC", "WVVI", "WVVIP", "WW", "WWAC", "WWD", "WWR", "WYNN", "XAIR", "XBIO",
    "XBIT", "XBIOW", "XCUR", "XEL", "XELA", "XELB", "XELC", "XENE", "XENT", "XERS",
    "XFOR", "XGN", "XMTR", "XNCR", "XNET", "XOMA", "XONE", "XPEL", "XPER", "XPEV",
    "XPOF", "XPON", "XRAY", "XRTX", "XSPA", "XT", "XTLB", "XTLY", "XTNT", "XXII",
    "XYF", "XYLD", "XYLG", "YAPO", "YAYO", "YGF", "YHGJ", "YIYI", "YJ", "YMAB",
    "YMAX", "YMM", "YORW", "YOSH", "YOU", "YSG", "YTEN", "YTRA", "YUM", "YUMC",
    "YVR", "YY", "Z", "ZAPP", "ZBAO", "ZBRA", "ZCMD", "ZDGE", "ZENV", "ZEPP",
    "ZETA", "ZEUS", "ZEV", "ZG", "ZH", "ZI", "ZION", "ZIONL", "ZIONO", "ZIONP",
    "ZIOP", "ZIXI", "ZKIN", "ZLAB", "ZM", "ZNTL", "ZOM", "ZOOM", "ZSAN", "ZTEK",
    "ZTO", "ZTS", "ZUMZ", "ZUO", "ZURA", "ZVRA", "ZYME", "ZYXI",
]


def get_all_companies() -> List[Dict]:
    """
    Get hardcoded list of 1000+ companies with basic info.
    
    Returns:
        List of company dicts with ticker, name, sector, industry
    """
    companies = []
    
    # Add S&P 500 companies with basic categorization
    for ticker in SP500_TICKERS:
        # Basic sector assignment based on ticker position in list
        if ticker in ["AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL",
                      "ADBE", "CRM", "CSCO", "ACN", "AMD", "INTC", "IBM", "QCOM", "INTU", "NOW",
                      "AMAT", "ADI", "LRCX", "KLAC", "SNPS", "CDNS", "MCHP", "NXPI", "FTNT", "ANSS",
                      "TXN", "MU", "PANW", "ADSK", "ROP", "PLTR", "WDAY", "TEAM", "DDOG", "SNOW",
                      "ZS", "NET", "CRWD", "ABNB", "UBER", "LYFT", "DASH", "COIN", "RBLX", "U"]:
            sector = "Tech"
        elif ticker in ["UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "ABT", "DHR", "PFE", "AMGN",
                        "BMY", "GILD", "CVS", "CI", "ELV", "HCA", "ISRG", "VRTX", "REGN", "ZTS",
                        "MRNA", "MCK", "COR", "IDXX", "IQV", "A", "DGX", "BDX", "SYK", "BSX",
                        "EW", "RMD", "HOLX", "MTD", "BAX", "WAT", "ALGN", "DXCM", "PODD", "INCY",
                        "BIIB", "TECH", "VTRS", "XRAY", "HUM", "CNC", "MOH", "UHS", "DVA", "ENOV"]:
            sector = "Pharma"
        elif ticker in ["BRK.B", "V", "MA", "JPM", "BAC", "WFC", "GS", "MS", "AXP", "SCHW",
                        "BLK", "SPGI", "C", "PGR", "CB", "MMC", "AON", "ICE", "CME", "MCO",
                        "PNC", "USB", "TFC", "COF", "AIG", "MET", "PRU", "AFL", "ALL", "TRV",
                        "FITB", "HBAN", "RF", "CFG", "KEY", "WTW", "BRO", "MKTX", "NDAQ", "CBOE"]:
            sector = "Finance"
        elif ticker in ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW", "TJX", "BKNG", "ABNB",
                        "CMG", "ORLY", "MAR", "GM", "F", "HLT", "YUM", "DPZ", "ROST", "LULU",
                        "AZO", "ULTA", "DG", "DLTR", "EBAY", "ETSY", "W", "CHWY", "CVNA", "KMX",
                        "WMT", "PG", "COST", "KO", "PEP", "PM", "MO", "MDLZ", "CL", "KMB",
                        "GIS", "K", "HSY", "SJM", "CAG", "CPB", "CHD", "CLX", "TSN", "HRL"]:
            sector = "Retail"
        else:
            sector = "Other"
        
        companies.append({
            'ticker': ticker,
            'name': f"{ticker} Corp",  # Simplified name
            'sector': sector,
            'industry': sector,
        })
    
    # Add biotech/tech companies (all are Pharma or Tech)
    for ticker in BIOTECH_TECH_TICKERS:
        # Biotech tickers are typically those with longer names or specific patterns
        if ticker in ["ACAD", "ALNY", "ALPN", "ARDX", "ARWR", "ARVN", "AXSM", "BCRX", "BGNE",
                      "BLUE", "BPMC", "CARA", "CLDX", "CORT", "CRBP", "CRIS", "CRSP", "CRTX",
                      "CVAC", "DNLI", "DRNA", "DVAX", "EDIT", "ETNB", "FATE", "FDMT", "FOLD",
                      "GTHX", "HCAT", "HOOK", "HROW", "IBRX", "IDYA", "IGMS", "IMAB", "IMNM",
                      "IMTX", "IPSC", "IRWD", "ITCI", "JNCE", "KALA", "KALV", "KPTI", "KRYS",
                      "KYMR", "LCTX", "LEGN", "LENZ", "LMNR", "LOGC", "LPTX", "LYEL", "MDGL",
                      "MGNX", "MIRM", "MRTX", "MRUS", "MRVI", "NTLA", "NVAX", "OCUL", "PGEN",
                      "PRTA", "PRTK", "PTCT", "PTGX", "PRVB", "REPL", "RGNX", "ROIV", "RXRX",
                      "SAGE", "SAVA", "SDGR", "SGMO", "SNDX", "SUPN", "TGTX", "VBIV", "VCEL",
                      "VKTX", "VRDN", "VYGR", "XLRN", "YMAB", "ZLAB", "ZNTL", "ZYME", "AGIO",
                      "ALLO", "ABUS", "APLS", "ATNM", "AUTL", "AVXL", "BEAM", "BPTH", "CMPS",
                      "CYTK", "DMTK", "ESPR", "EXEL", "FGEN", "GLPG", "HALO", "IONS", "KROS",
                      "LXRX", "MNKD", "NBIX", "NKTR", "NVCR", "OPCH", "PBYI", "PCRX", "RARE",
                      "RLAY", "RVMD", "SGEN", "SRPT", "STOK", "TBPH", "TYME", "VCYT", "VRTX",
                      "ACHC", "ADMA", "ALHC", "AMN", "CRVL", "ENSG", "EVH", "GMED", "HIMS",
                      "KNSA", "LMAT", "OMCL", "PDCO", "PNTG", "PRVA", "RDNT", "SGRY", "TMDX"]:
            sector = "Pharma"
        else:
            sector = "Tech"
        
        companies.append({
            'ticker': ticker,
            'name': f"{ticker} Inc",
            'sector': sector,
            'industry': sector,
        })
    
    logger.info(f"Generated {len(companies)} companies")
    return companies


def populate_companies(dm: DataManager, companies: List[Dict]) -> int:
    """
    Add companies to database using DataManager.
    
    Returns:
        Count of companies added
    """
    logger.info(f"Adding {len(companies)} companies to database...")
    
    added = 0
    skipped = 0
    errors = 0
    
    for i, company in enumerate(companies):
        try:
            # Check if company already exists
            existing = dm.get_company(company['ticker'])
            
            if existing:
                skipped += 1
                if i % 100 == 0:
                    logger.info(f"Progress: {i}/{len(companies)} ({added} added, {skipped} skipped)")
                continue
            
            # Add company
            dm.add_company(
                ticker=company['ticker'],
                name=company['name'],
                sector=company['sector'],
                industry=company['industry'],
                tracked=True
            )
            
            added += 1
            
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{len(companies)} ({added} added, {skipped} skipped)")
        
        except Exception as e:
            logger.error(f"Error adding company {company['ticker']}: {e}")
            errors += 1
            continue
    
    logger.success(f"Companies added: {added}, skipped: {skipped}, errors: {errors}")
    return added


def run_scanner_and_save_events(
    scanner_name: str,
    scanner_fn,
    tickers: List[str],
    companies_dict: Dict[str, Dict],
    dm: DataManager,
    limit_per_ticker: int = 3
) -> int:
    """
    Run a scanner and save all returned events to database.
    
    Args:
        scanner_name: Name of scanner (for logging)
        scanner_fn: Scanner function to call
        tickers: List of tickers to scan
        companies_dict: Dict mapping ticker -> company info
        dm: DataManager instance
        limit_per_ticker: Max events per ticker
        
    Returns:
        Count of events saved
    """
    logger.info(f"Running scanner: {scanner_name}")
    
    try:
        # Run scanner
        events = scanner_fn(
            tickers=tickers,
            companies=companies_dict,
            limit_per_ticker=limit_per_ticker
        )
        
        logger.info(f"{scanner_name} returned {len(events)} events")
        
        # Save events using DataManager
        saved = 0
        skipped = 0
        errors = 0
        
        for event in events:
            try:
                # Check if event already exists (by raw_id)
                existing = dm.get_events(
                    ticker=event['ticker'],
                    limit=1000  # Check recent events
                )
                
                # Check for duplicate by raw_id
                if any(e.get('raw_id') == event.get('raw_id') for e in existing):
                    skipped += 1
                    continue
                
                # Add event
                dm.add_event(
                    ticker=event['ticker'],
                    company_name=event['company_name'],
                    event_type=event['event_type'],
                    title=event['title'],
                    date=event['date'],
                    source=event['source'],
                    source_url=event['source_url'],
                    description=event.get('description', ''),
                    raw_id=event.get('raw_id'),
                    source_scanner=event.get('source_scanner'),
                    sector=event.get('sector'),
                    info_tier=event.get('info_tier'),
                    info_subtype=event.get('info_subtype'),
                    metadata=event.get('metadata')
                )
                
                saved += 1
            
            except Exception as e:
                logger.error(f"Error saving event: {e}")
                errors += 1
                continue
        
        logger.success(f"{scanner_name}: {saved} events saved, {skipped} skipped, {errors} errors")
        return saved
    
    except Exception as e:
        logger.error(f"Scanner {scanner_name} failed: {e}")
        return 0


def run_all_scanners(
    dm: DataManager,
    tickers: List[str],
    companies_dict: Dict[str, Dict],
    batch_size: int = 50
) -> int:
    """
    Run all scanners in batches and save events.
    
    Args:
        dm: DataManager instance
        tickers: List of all tickers to scan
        companies_dict: Dict mapping ticker -> company info
        batch_size: Number of tickers per batch
        
    Returns:
        Total count of events saved
    """
    logger.info(f"Running all scanners for {len(tickers)} tickers in batches of {batch_size}")
    
    total_events = 0
    
    # Define scanners with their configurations
    scanners = [
        ("SEC 8-K", scan_sec_8k, 2),
        ("SEC 10-Q", scan_sec_10q, 1),
        ("Earnings", scan_earnings_calls, 2),
        ("FDA", scan_fda, 2),
        ("Guidance", scan_guidance, 1),
        ("M&A", scan_ma, 1),
        ("Dividend/Buyback", scan_dividend_buyback, 1),
        ("Product Launch", scan_product_launch, 1),
        ("Press Releases", scan_press, 2),
    ]
    
    # Run each scanner
    for scanner_name, scanner_fn, limit_per_ticker in scanners:
        logger.info(f"\n{'='*60}\nScanner: {scanner_name}\n{'='*60}")
        
        # Process tickers in batches to avoid overwhelming APIs
        for batch_start in range(0, len(tickers), batch_size):
            batch_end = min(batch_start + batch_size, len(tickers))
            batch_tickers = tickers[batch_start:batch_end]
            
            logger.info(f"Processing batch {batch_start//batch_size + 1}/{(len(tickers)-1)//batch_size + 1} "
                       f"({len(batch_tickers)} tickers)")
            
            # Run scanner on batch
            events_saved = run_scanner_and_save_events(
                scanner_name=scanner_name,
                scanner_fn=scanner_fn,
                tickers=batch_tickers,
                companies_dict=companies_dict,
                dm=dm,
                limit_per_ticker=limit_per_ticker
            )
            
            total_events += events_saved
            
            # Rate limiting between batches
            if batch_end < len(tickers):
                logger.info("Sleeping 5s before next batch...")
                time.sleep(5)
        
        # Rate limiting between scanners
        logger.info(f"Completed {scanner_name}. Sleeping 10s before next scanner...")
        time.sleep(10)
    
    logger.success(f"\nAll scanners completed! Total events saved: {total_events}")
    return total_events


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Populate database with 1000+ companies and real events"
    )
    parser.add_argument(
        '--skip-companies',
        action='store_true',
        help='Skip company population (only run scanners)'
    )
    parser.add_argument(
        '--skip-events',
        action='store_true',
        help='Skip event scanning (only add companies)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of tickers per batch when scanning (default: 50)'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("POPULATE 1000+ COMPANIES WITH REAL EVENTS")
    logger.info("=" * 80)
    
    # Initialize DataManager
    dm = DataManager()
    
    # Get all companies
    companies = get_all_companies()
    logger.info(f"Total companies to process: {len(companies)}")
    
    # Step 1: Add companies to database
    if not args.skip_companies:
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Adding companies to database")
        logger.info("=" * 80)
        
        companies_added = populate_companies(dm, companies)
        logger.success(f"Companies added: {companies_added}")
    else:
        logger.info("Skipping company population (--skip-companies)")
    
    # Step 2: Run scanners and save events
    if not args.skip_events:
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Running scanners and saving events")
        logger.info("=" * 80)
        
        # Create companies dict for scanner input
        companies_dict = {
            c['ticker']: {
                'name': c['name'],
                'sector': c['sector'],
                'industry': c['industry']
            }
            for c in companies
        }
        
        # Get list of tickers
        tickers = [c['ticker'] for c in companies]
        
        # Run all scanners
        total_events = run_all_scanners(
            dm=dm,
            tickers=tickers,
            companies_dict=companies_dict,
            batch_size=args.batch_size
        )
        
        logger.success(f"Total events saved: {total_events}")
    else:
        logger.info("Skipping event scanning (--skip-events)")
    
    logger.info("\n" + "=" * 80)
    logger.success("POPULATION COMPLETE!")
    logger.info("=" * 80)
    
    # Print summary statistics
    all_companies = dm.get_companies()
    all_events = dm.get_events(limit=10000)
    
    logger.info(f"\nFinal Statistics:")
    logger.info(f"  Total companies in database: {len(all_companies)}")
    logger.info(f"  Total events in database: {len(all_events)}")
    
    # Count events by scanner
    scanner_counts = {}
    for event in all_events:
        scanner = event.get('source_scanner', 'unknown')
        scanner_counts[scanner] = scanner_counts.get(scanner, 0) + 1
    
    logger.info(f"\nEvents by scanner:")
    for scanner, count in sorted(scanner_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {scanner}: {count}")


if __name__ == "__main__":
    main()
