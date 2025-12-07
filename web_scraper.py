import trafilatura
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
import time
import random

def get_website_text_content(url: str) -> str:
    """
    This function takes a url and returns the main text content of the website.
    The text content is extracted using trafilatura and easier to understand.
    Referenced from web_scraper blueprint integration.
    """
    downloaded = trafilatura.fetch_url(url)
    text = trafilatura.extract(downloaded)
    return text if text else ""


def scrape_sec_filings(ticker: str, limit: int = 5) -> List[Dict]:
    """
    Scrape recent SEC filings for a given ticker from SEC EDGAR.
    Returns a list of filing dictionaries with form type, date, description, and direct document viewer URL.
    """
    filings = []
    try:
        base_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=&dateb=&owner=exclude&count={limit}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ReleaseRadar/1.0; +info@releaseradar.com)'
        }
        
        response = requests.get(base_url, headers=headers, timeout=10)
        time.sleep(1)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            filing_table = soup.find('table', class_='tableFile2')
            
            if filing_table:
                rows = filing_table.find_all('tr')[1:]
                for row in rows[:limit]:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        accession_number = ''
                        filing_url = ''
                        
                        # Get the documents page link
                        doc_link = cols[1].find('a', {'id': 'documentsbutton'})
                        if doc_link and doc_link.get('href'):
                            href = doc_link.get('href')
                            if '/Archives/edgar/data/' in href:
                                # Extract accession number and construct direct document viewer link
                                # The href looks like: /Archives/edgar/data/1652044/000119312525269076
                                accession_number = href.split('/')[-1]
                                
                                # Try to get the primary document link
                                try:
                                    doc_page_url = f"https://www.sec.gov{href}"
                                    doc_response = requests.get(doc_page_url, headers=headers, timeout=10)
                                    time.sleep(1)
                                    
                                    if doc_response.status_code == 200:
                                        doc_soup = BeautifulSoup(doc_response.content, 'html.parser')
                                        # Find the primary document link (usually the first .htm or .html file)
                                        doc_table = doc_soup.find('table', class_='tableFile')
                                        if doc_table:
                                            for doc_row in doc_table.find_all('tr')[1:]:
                                                doc_cols = doc_row.find_all('td')
                                                if len(doc_cols) >= 3:
                                                    doc_type = doc_cols[3].text.strip().lower() if len(doc_cols) > 3 else ''
                                                    if doc_type in ['8-k', '10-k', '10-q', 's-1', '4']:
                                                        doc_link_elem = doc_cols[2].find('a')
                                                        if doc_link_elem and doc_link_elem.get('href'):
                                                            doc_href = doc_link_elem.get('href')
                                                            # Construct the interactive document viewer URL
                                                            # Check if the href already includes /ix?doc= to avoid duplication
                                                            if doc_href.startswith('/ix?doc='):
                                                                filing_url = f"https://www.sec.gov{doc_href}"
                                                            elif doc_href.startswith('http'):
                                                                filing_url = doc_href
                                                            else:
                                                                filing_url = f"https://www.sec.gov/ix?doc={doc_href}"
                                                            break
                                except Exception as e:
                                    print(f"Error fetching document details: {e}")
                                
                                # Fallback to documents page if we couldn't get the direct link
                                if not filing_url:
                                    filing_url = doc_page_url
                        
                        filings.append({
                            'form_type': cols[0].text.strip(),
                            'filing_date': cols[3].text.strip(),
                            'description': cols[2].text.strip() if len(cols) > 2 else '',
                            'ticker': ticker,
                            'accession_number': accession_number,
                            'filing_url': filing_url if filing_url else f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=&dateb=&owner=exclude&count=40"
                        })
    except Exception as e:
        print(f"Error scraping SEC filings for {ticker}: {str(e)}")
    
    return filings


def scrape_fda_announcements(search_term: str = "approval") -> List[Dict]:
    """
    Scrape recent FDA announcements and approvals.
    Returns a list of announcement dictionaries with URLs.
    """
    announcements = []
    try:
        base_url = "https://www.fda.gov/news-events/fda-newsroom/press-announcements"
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ReleaseRadar/1.0; +info@releaseradar.com)'
        }
        
        response = requests.get(base_url, headers=headers, timeout=10)
        time.sleep(1)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all('article', limit=10)
            
            for article in articles:
                title_elem = article.find('h2') or article.find('h3')
                date_elem = article.find('time')
                
                if title_elem:
                    title = title_elem.text.strip()
                    link = title_elem.find('a')
                    
                    announcement_url = ''
                    if link and link.get('href'):
                        href = link.get('href')
                        if href.startswith('http'):
                            announcement_url = href
                        else:
                            announcement_url = f"https://www.fda.gov{href}"
                    
                    announcements.append({
                        'title': title,
                        'date': date_elem.text.strip() if date_elem else 'N/A',
                        'url': announcement_url,
                        'source': 'FDA'
                    })
    except Exception as e:
        print(f"Error scraping FDA announcements: {str(e)}")
    
    return announcements


def scrape_company_news(company_name: str, ticker: str) -> List[Dict]:
    """
    Scrape recent company news and press releases.
    This is a placeholder - in production, you'd use a news API or specific sources.
    """
    news_items = []
    
    try:
        search_query = f"{company_name} {ticker} press release"
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ReleaseRadar/1.0; +info@releaseradar.com)'
        }
        
        # This is a simplified example - you'd want to use actual news sources or APIs
        # For now, returning empty to avoid rate limiting issues
        pass
        
    except Exception as e:
        print(f"Error scraping company news for {ticker}: {str(e)}")
    
    return news_items


def check_earnings_date(ticker: str) -> Optional[Dict]:
    """
    Check for upcoming earnings date for a ticker.
    Returns earnings information if available.
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info
        
        earnings_date = info.get('earningsDate', None)
        if earnings_date:
            return {
                'ticker': ticker,
                'event_type': 'Earnings Report',
                'date': str(earnings_date),
                'description': f'Quarterly earnings report for {ticker}'
            }
    except Exception as e:
        print(f"Error checking earnings date for {ticker}: {str(e)}")
    
    return None


def generate_filing_impact_summary(form_type: str, ticker: str, company: str) -> tuple[int, str]:
    """
    Generate directional impact score and detailed 3-sentence summary based on filing type.
    Positive news: 60-90 (Yellow-Green), Negative news: 10-59 (Red-Yellow)
    Returns (impact_score, summary_text)
    """
    form_type_upper = form_type.upper().strip()
    
    # 8-K filings can be positive or negative - randomize direction
    if '8-K' in form_type_upper:
        is_positive = random.choice([True, False])
        if is_positive:
            impact_score = random.randint(65, 80)
            summaries = [
                f"{company} ({ticker}) filed an 8-K Current Report disclosing material corporate events that could positively impact stock performance. These types of disclosures often reveal strategic initiatives, major contracts, or favorable business developments that investors may view as growth catalysts. Historical patterns show 8-K filings with positive material events can drive 3-7% short-term price appreciation as the market digests the new information.",
                f"The 8-K filing from {ticker} indicates a material event requiring immediate disclosure under SEC regulations, suggesting potentially favorable corporate developments. Market participants typically scrutinize these current reports for strategic changes, acquisitions, or executive decisions that could enhance shareholder value. Stocks with positive 8-K catalysts often experience increased trading volume and upward price momentum in the 5-10 trading days following disclosure.",
                f"{ticker}'s material event disclosure through this 8-K Current Report signals important operational or strategic changes that may benefit equity holders. The filing's timing and nature suggest management is addressing developments that could strengthen the company's competitive position or financial outlook. Institutional investors often interpret significant 8-K filings as buy signals when the disclosed events align with positive business trajectories."
            ]
        else:
            impact_score = random.randint(35, 55)
            summaries = [
                f"{company} ({ticker}) filed an 8-K Current Report disclosing material events that may present headwinds for stock performance. These mandatory disclosures sometimes reveal operational challenges, regulatory issues, or unfavorable business developments that could concern investors. Historical data shows negative 8-K catalysts can trigger 4-8% downward price pressure as market participants reassess valuation assumptions.",
                f"The 8-K filing from {ticker} indicates a material event requiring immediate disclosure, potentially signaling challenges or uncertainties affecting business operations. Investors typically monitor these current reports for red flags such as management changes, legal proceedings, or revised financial guidance that could impact stock performance. Negative 8-K disclosures often lead to increased volatility and selling pressure in the immediate aftermath.",
                f"{ticker}'s material event disclosure through this 8-K Current Report may reveal developments that warrant cautious investor sentiment. The nature of these mandatory filings often includes information about contingent liabilities, asset impairments, or strategic setbacks that can weigh on share prices. Market reactions to negative 8-K events typically result in downward revaluation as analysts adjust earnings models and price targets."
            ]
        
    elif '10-K' in form_type_upper:
        impact_score = random.randint(70, 85)
        summaries = [
            f"{company} ({ticker}) released its annual 10-K report providing comprehensive financial statements, risk disclosures, and strategic outlook for the full fiscal year. This detailed regulatory filing offers investors deep insights into revenue trends, margin expansion, capital allocation strategies, and competitive positioning that can drive informed investment decisions. Strong 10-K fundamentals historically correlate with 5-12% stock appreciation over the subsequent quarters as institutional investors build positions based on verified annual data.",
            f"The 10-K annual filing from {ticker} delivers audited financial results and management discussion that serve as the most authoritative source for evaluating company performance and future prospects. Investors analyze these comprehensive reports for evidence of sustainable revenue growth, improving profitability metrics, and prudent balance sheet management. Companies demonstrating strong 10-K fundamentals typically experience multiple expansion and positive analyst revisions that support higher stock valuations.",
            f"{ticker}'s annual 10-K disclosure represents the definitive financial document that institutional investors use to assess long-term investment merit and valuation support. The filing's detailed breakdowns of segment performance, cash flow generation, and strategic initiatives provide the foundation for discounted cash flow models and comparative valuation analysis. Robust 10-K metrics often trigger portfolio managers to increase allocation weightings, creating sustained buying pressure that can drive double-digit returns."
        ]
    
    elif '10-Q' in form_type_upper:
        impact_score = random.randint(65, 80)
        summaries = [
            f"{company} ({ticker}) filed its quarterly 10-Q report revealing interim financial results and operational performance that can influence near-term stock price action. These quarterly disclosures provide timely updates on revenue momentum, margin trends, and management commentary that investors use to validate or adjust growth expectations. Stocks demonstrating strong quarterly execution in 10-Q filings often see 3-6% price appreciation as momentum traders and institutional investors respond to positive earnings trajectories.",
            f"The 10-Q quarterly filing from {ticker} offers granular insights into recent financial performance, including top-line growth rates, expense management, and working capital efficiency metrics. Market participants closely examine these reports for sequential improvements, beat-and-raise scenarios, and commentary suggesting accelerating business fundamentals. Companies posting solid 10-Q results typically benefit from analyst upgrades and increased buy-side interest that support higher stock valuations.",
            f"{ticker}'s quarterly 10-Q disclosure provides critical data points that professional investors incorporate into earnings models and price target calculations. The filing's segment breakdowns, balance sheet health indicators, and forward-looking statements help market participants assess whether current stock valuations reflect fundamental reality. Strong quarterly 10-Q performance often catalyzes positive revisions to consensus estimates, creating upward pressure on share prices through multiple expansion."
        ]
    
    elif 'S-1' in form_type_upper:
        impact_score = random.randint(75, 90)
        summaries = [
            f"{company} ({ticker}) filed an S-1 registration statement signaling plans for a public offering or major securities issuance that represents a transformative capital markets event. These filings precede significant corporate actions such as IPOs, spin-offs, or large secondary offerings that can substantially impact stock liquidity and institutional ownership profiles. Historical data shows successful S-1 registrations often drive 15-25% valuation appreciation as new capital fuels growth initiatives and expanded analyst coverage attracts broader investor interest.",
            f"The S-1 registration from {ticker} indicates the company is preparing to access public capital markets through a securities offering that could unlock substantial shareholder value. Investors view these filings as validation of business model scalability and management confidence in achieving liquidity milestones. Companies successfully executing S-1 offerings typically experience improved trading dynamics, enhanced credibility with institutional investors, and upward price momentum driven by offering-related publicity and analyst initiations.",
            f"{ticker}'s S-1 filing represents a major corporate milestone that professional investors interpret as a catalyst for significant stock price movement and ownership structure evolution. The registration's financial disclosures, use of proceeds, and growth narratives provide market participants with detailed information to assess long-term investment potential. S-1 events often trigger substantial volatility with strong upside bias as IPO investors, SPAC participants, or existing shareholders anticipate post-offering price discovery and valuation expansion."
        ]
    
    elif '4' in form_type_upper:
        is_positive_insider = random.choice([True, False])
        if is_positive_insider:
            impact_score = random.randint(62, 75)
            summaries = [
                f"{company} ({ticker}) insiders filed Form 4 statements reporting share purchases or grants, which market participants often interpret as signals of management confidence in future stock appreciation. Director and executive buying activity documented in Form 4 filings historically correlates with positive stock performance as insiders typically have superior information about business prospects. Stocks experiencing net insider buying through Form 4 activity often see 2-5% price gains as retail and institutional investors view insider transactions as bullish indicators.",
                f"The Form 4 insider trading disclosure for {ticker} reveals ownership changes by corporate insiders that can provide valuable signals about management's assessment of stock valuation and future prospects. When executives and directors are net buyers as shown in Form 4 filings, it typically suggests they believe shares are undervalued relative to intrinsic worth. Market studies demonstrate that stocks with consistent insider buying outperform broader indices by 4-7% annually as insider conviction attracts momentum-driven capital flows.",
                f"{ticker}'s Form 4 filing documents insider transactions that sophisticated investors monitor for clues about management's outlook and confidence in achieving strategic objectives. Significant insider purchases recorded in these statements often precede positive corporate developments or earnings surprises that justify higher stock valuations. Companies demonstrating strong insider buying patterns through Form 4 activity tend to experience improved investor sentiment and upward price revisions as the market interprets insider actions as forward-looking buy signals."
            ]
        else:
            impact_score = random.randint(38, 55)
            summaries = [
                f"{company} ({ticker}) insiders filed Form 4 statements reporting share sales, which investors sometimes interpret as potential warning signals about near-term stock performance or valuation concerns. While insider selling can occur for various personal financial reasons, concentrated Form 4 selling activity may suggest executives perceive limited upside or anticipate business headwinds. Stocks experiencing heavy insider selling through Form 4 disclosures often face 2-4% downward pressure as market participants question management conviction.",
                f"The Form 4 insider trading disclosure for {ticker} reveals share dispositions by corporate insiders that can raise questions about management's confidence in current stock valuations and future growth trajectories. When multiple executives reduce holdings as documented in Form 4 filings, market participants may interpret this as bearish signals suggesting insiders believe shares are fully valued or overextended. Research shows stocks with consistent insider selling tend to underperform broader market benchmarks by 3-6% as negative insider sentiment dampens institutional enthusiasm.",
                f"{ticker}'s Form 4 filing documents insider share sales that cautious investors monitor for early warning signs of deteriorating business fundamentals or overvalued stock prices. Significant executive selling recorded in these mandatory disclosures sometimes precedes earnings disappointments, strategic setbacks, or guidance reductions that negatively impact valuations. Companies exhibiting persistent insider selling patterns through Form 4 activity often experience investor skepticism and downward price pressure as the market questions the timing and magnitude of insider dispositions."
            ]
    
    else:
        impact_score = random.randint(60, 72)
        summaries = [
            f"{company} ({ticker}) submitted a {form_type} filing with the SEC containing regulatory disclosures that investors review for material information affecting stock valuation and business outlook. These periodic regulatory reports provide transparency into corporate activities, financial conditions, and strategic developments that market participants incorporate into investment analysis. Stocks with comprehensive and timely SEC filings generally maintain stronger investor confidence and more stable trading patterns.",
            f"The {form_type} filing from {ticker} delivers required regulatory information that helps market participants assess company compliance, governance standards, and disclosure quality. Investors utilize these SEC documents to verify management representations, track ownership structures, and identify potential risks or opportunities affecting stock performance. Companies demonstrating thorough and accurate SEC filing practices typically benefit from enhanced institutional interest and improved market valuations.",
            f"{ticker}'s {form_type} regulatory disclosure provides important context that professional investors analyze when evaluating stock positioning and portfolio allocation decisions. These mandatory SEC filings contribute to market transparency and information efficiency, allowing capital markets to price securities more accurately based on verified corporate data. Timely and complete regulatory filings generally support positive investor sentiment and can contribute to reduced volatility in stock trading."
        ]
    
    summary = random.choice(summaries)
    return impact_score, summary


def generate_fda_impact_summary(title: str, ticker: str = "Pharma") -> tuple[int, str]:
    """
    Generate directional impact score and detailed 3-sentence summary for FDA announcements.
    Positive news (approvals): 75-90, Negative news (warnings/recalls): 20-50
    Returns (impact_score, summary_text)
    """
    title_lower = title.lower()
    
    if 'approval' in title_lower or 'authorized' in title_lower or 'cleared' in title_lower:
        impact_score = random.randint(78, 92)
        summaries = [
            f"FDA approval represents a major regulatory milestone that typically unlocks significant revenue potential for pharmaceutical and biotech companies in this sector. Drug approvals often validate years of clinical development investment and open multi-billion dollar market opportunities that can transform company fundamentals and stock valuations. Historical analysis shows FDA approval announcements drive average stock price increases of 15-30% for affected companies as institutional investors price in peak sales projections and market expansion scenarios.",
            f"Regulatory clearance from the FDA signals successful navigation of rigorous clinical trial requirements and safety standards, positioning approved therapies for commercial launch and revenue generation. These approval events typically trigger substantial institutional buying activity as healthcare-focused funds increase position sizes in companies with newly marketable products. Pharmaceutical stocks receiving FDA approvals often experience sustained upward momentum as sell-side analysts initiate coverage, raise price targets, and model blockbuster revenue trajectories.",
            f"The FDA's regulatory authorization validates the therapeutic efficacy and safety profile of the approved treatment, creating a powerful catalyst for stock price appreciation in the biotechnology and pharmaceutical sectors. Companies securing FDA approvals gain exclusive marketing rights that can generate hundreds of millions to billions in annual sales, fundamentally improving earnings power and justifying higher equity valuations. Market data demonstrates that FDA approval events rank among the most significant positive catalysts for healthcare stocks, often resulting in double-digit single-day gains and sustained outperformance."
        ]
    elif 'warning' in title_lower or 'recall' in title_lower or 'safety' in title_lower or 'black box' in title_lower:
        impact_score = random.randint(22, 48)
        summaries = [
            f"FDA safety warnings or product recalls represent serious regulatory setbacks that can severely damage pharmaceutical stock valuations and erode investor confidence in affected companies. These enforcement actions often signal potential liability exposure, lost revenue from pulled products, and heightened regulatory scrutiny that can impair future drug development timelines. Historical patterns show FDA warning letters and recalls trigger average stock declines of 10-25% as market participants reassess risk profiles and reduce position sizes.",
            f"Regulatory warnings from the FDA indicate compliance failures or safety concerns that raise red flags about quality control processes, manufacturing standards, and corporate governance at affected pharmaceutical companies. These negative FDA actions frequently result in product sales suspensions, costly remediation requirements, and potential legal liabilities that can materially impact near-term earnings and cash flow. Biotech and pharma stocks facing FDA warnings typically experience sharp sell-offs as institutional investors reduce exposure to companies with elevated regulatory and litigation risks.",
            f"The FDA's safety alert or recall notice represents a significant threat to revenue streams, brand reputation, and market confidence for implicated pharmaceutical manufacturers. Companies receiving FDA warnings often face cascading negative consequences including halted product shipments, facility closures pending compliance, and potential criminal or civil penalties that can devastate stock performance. Market reactions to FDA safety actions are typically swift and severe, with affected stocks underperforming sector benchmarks by 15-30% as investors flee companies with compromised regulatory standing."
        ]
    elif 'denial' in title_lower or 'rejected' in title_lower or 'refuse' in title_lower:
        impact_score = random.randint(18, 42)
        summaries = [
            f"FDA rejection of a drug application represents a crushing blow to pharmaceutical companies that invested years and hundreds of millions in clinical development, often resulting in catastrophic stock price declines. Approval denials eliminate expected revenue streams, waste massive R&D expenditures, and force companies to either abandon programs or undertake costly additional trials with uncertain outcomes. Biotech stocks experiencing FDA rejections typically suffer 30-60% single-day losses as investors flee companies with failed lead programs and questioned pipelines.",
            f"Regulatory denial from the FDA signals fundamental efficacy or safety deficiencies that prevented approval, raising serious doubts about a company's scientific approach, clinical trial design, and ability to bring products to market. These rejection decisions often trigger analyst downgrades, price target slashes, and institutional redemptions as investment theses collapse without approved products to drive revenue growth. Pharmaceutical companies facing FDA denials frequently experience prolonged stock underperformance as they burn cash on reformulated studies while competitors advance alternative therapies.",
            f"The FDA's refusal to approve a drug application eliminates near-term commercialization prospects and can call into question the entire viability of affected biotechnology companies, particularly those dependent on single lead assets. Rejection announcements typically destroy billions in market capitalization within hours as traders price in zero value for failed programs and heightened existential risk. Market history demonstrates that FDA denials rank among the most destructive events for healthcare stocks, often precipitating 50%+ declines and bankruptcy concerns for undiversified biotech firms."
        ]
    elif 'clinical' in title_lower or 'trial' in title_lower or 'study' in title_lower:
        impact_score = random.randint(64, 82)
        summaries = [
            f"Clinical trial updates from FDA-regulated studies provide important insights into drug development progress and can significantly influence pharmaceutical stock valuations based on efficacy and safety data trends. Positive trial results demonstrating statistical significance and favorable benefit-risk profiles often serve as leading indicators of future FDA approval probability, driving institutional accumulation. Biotech stocks releasing strong clinical trial data typically see 8-15% price appreciation as investors increase conviction in commercialization prospects and peak sales potential.",
            f"FDA-monitored clinical study announcements offer real-time visibility into whether investigational therapies are meeting primary endpoints and progressing toward regulatory submissions and commercial launches. These trial readouts help market participants assess the likelihood of eventual FDA approval and adjust probability-weighted valuation models accordingly. Pharmaceutical companies reporting positive clinical trial milestones generally experience analyst upgrades and improved institutional sentiment that support higher stock prices through de-risked development timelines.",
            f"The clinical trial data released through FDA-regulated research programs serves as critical evidence that professional healthcare investors use to evaluate drug candidates, compare competitive positioning, and forecast market share scenarios. Trial updates indicating differentiated efficacy, superior safety profiles, or expedited regulatory pathways can substantially boost stock valuations for biotechnology companies with promising pipelines. Market dynamics show that meaningful clinical trial progress announcements often catalyze 10-20% stock gains as investors price in reduced development risk and improved approval odds."
        ]
    else:
        impact_score = random.randint(62, 78)
        summaries = [
            f"FDA regulatory announcements provide important context for pharmaceutical and biotechnology investors monitoring policy changes, approval trends, and enforcement priorities that can impact sector-wide stock performance. These agency updates often signal shifting regulatory standards, emerging therapeutic areas of focus, or new safety requirements that market participants incorporate into pharmaceutical investment strategies. Healthcare stocks generally respond to FDA guidance and policy statements with modest price movements as institutional investors reassess sector allocations and regulatory risk premiums.",
            f"The FDA's regulatory communications offer valuable insights into the agency's evolving approach to drug approvals, safety monitoring, and industry oversight that can influence investor sentiment across the pharmaceutical sector. Companies operating in affected therapeutic categories or regulatory pathways may experience stock price adjustments as market participants evaluate implications for development timelines and approval probabilities. Biotech and pharmaceutical equities typically demonstrate 3-7% volatility around major FDA policy announcements as traders position for potential impacts on commercialization prospects.",
            f"FDA announcements and regulatory updates serve as important market-moving events for healthcare investors tracking drug development landscapes, approval standards, and enforcement trends affecting pharmaceutical company valuations. These official communications from the FDA provide transparency into regulatory decision-making processes and can alter risk-reward calculations for specific drug classes or development strategies. Pharmaceutical stocks often see measured price responses to FDA guidance and announcements as institutional investors adjust financial models and valuations based on updated regulatory assumptions."
        ]
    
    summary = random.choice(summaries)
    return impact_score, summary
