#!/usr/bin/env python3
"""
Alternative Data Collection Solutions for Car Cover Information
Multiple approaches when direct scraping is blocked
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import random
from datetime import datetime
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# ============================================================================
# SOLUTION 1: SELENIUM WITH UNDETECTED CHROME DRIVER
# ============================================================================

class SeleniumOLXScraper:
    def __init__(self):
        self.base_url = "https://www.olx.in"
        self.search_url = "https://www.olx.in/items/q-car-cover"
        self.driver = None
        
    def setup_driver(self):
        """Setup undetected Chrome driver"""
        try:
            print("🚀 Setting up undetected Chrome driver...")
            
            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Optional: Run in headless mode (comment out to see browser)
            # options.add_argument("--headless")
            
            self.driver = uc.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("✅ Driver setup complete")
            return True
            
        except Exception as e:
            print(f"❌ Driver setup failed: {e}")
            return False
    
    def scrape_with_selenium(self, max_pages=3):
        """Scrape using Selenium"""
        if not self.setup_driver():
            return []
        
        all_listings = []
        
        try:
            for page in range(1, max_pages + 1):
                print(f"\n📄 Scraping page {page} with Selenium...")
                
                if page == 1:
                    url = self.search_url
                else:
                    url = f"{self.search_url}?page={page}"
                
                self.driver.get(url)
                
                # Wait for page to load
                time.sleep(random.uniform(3, 6))
                
                # Wait for listings to appear
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "a"))
                    )
                except:
                    print("  ⚠ Timeout waiting for page elements")
                
                # Extract listings
                page_listings = self.extract_selenium_listings()
                
                if page_listings:
                    all_listings.extend(page_listings)
                    print(f"  ✅ Found {len(page_listings)} listings on page {page}")
                else:
                    print(f"  ❌ No listings found on page {page}")
                    if page == 1:
                        # Save page source for debugging
                        with open('selenium_debug.html', 'w', encoding='utf-8') as f:
                            f.write(self.driver.page_source)
                        print("  📄 Saved page source as selenium_debug.html")
                
                # Random delay between pages
                if page < max_pages:
                    delay = random.uniform(5, 10)
                    print(f"  ⏳ Waiting {delay:.1f}s...")
                    time.sleep(delay)
        
        finally:
            if self.driver:
                self.driver.quit()
        
        return all_listings
    
    def extract_selenium_listings(self):
        """Extract listings from current page"""
        listings = []
        
        # Try multiple selectors
        selectors = [
            '[data-aut-id="itemBox"]',
            '.EIR5N',
            'a[href*="/item/"]'
        ]
        
        for selector in selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"  ✓ Found {len(elements)} elements with selector: {selector}")
                
                for element in elements:
                    try:
                        listing = self.parse_selenium_element(element)
                        if listing:
                            listings.append(listing)
                    except Exception as e:
                        continue
                
                break
        
        return self.deduplicate_listings(listings)
    
    def parse_selenium_element(self, element):
        """Parse individual listing element"""
        try:
            listing = {}
            
            # Get all text from element
            element_text = element.text
            element_html = element.get_attribute('outerHTML')
            
            # Try to find link
            link_elem = element if element.tag_name == 'a' else element.find_element(By.TAG_NAME, 'a')
            href = link_elem.get_attribute('href') if link_elem else None
            
            if not href or '/item/' not in href:
                return None
            
            listing['link'] = href
            
            # Extract title from link text or nearby elements
            title = element_text.split('\n')[0] if element_text else ""
            if len(title) < 5:
                title_elem = element.find_element(By.CSS_SELECTOR, 'h2, h3, h4, span[title]')
                title = title_elem.text if title_elem else ""
            
            if len(title) < 5:
                return None
            
            listing['title'] = title.strip()
            
            # Extract price
            price_match = re.search(r'₹[\d,]+|Rs\.?\s*[\d,]+', element_text)
            listing['price'] = price_match.group() if price_match else "N/A"
            
            # Extract location
            location_match = re.search(r'\b[A-Z][a-z]+,\s*[A-Z][a-z]+\b', element_text)
            listing['location'] = location_match.group() if location_match else "N/A"
            
            # Extract date
            date_match = re.search(r'today|yesterday|\d+\s*(day|hour)s?\s*ago', element_text, re.I)
            listing['date'] = date_match.group() if date_match else "N/A"
            
            # Try to find image
            try:
                img_elem = element.find_element(By.TAG_NAME, 'img')
                listing['image_url'] = img_elem.get_attribute('src') or "N/A"
            except:
                listing['image_url'] = "N/A"
            
            return listing
            
        except Exception as e:
            return None
    
    def deduplicate_listings(self, listings):
        """Remove duplicates"""
        unique_listings = []
        seen_links = set()
        
        for listing in listings:
            link = listing.get('link', '')
            if link and link not in seen_links:
                unique_listings.append(listing)
                seen_links.add(link)
        
        return unique_listings

# ============================================================================
# SOLUTION 2: API-BASED APPROACH (Check for unofficial APIs)
# ============================================================================

class APIBasedScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9'
        })
    
    def search_olx_api(self, query="car cover", location="", limit=50):
        """Try to find and use OLX's mobile/internal API"""
        print(f"🔍 Searching for API endpoints...")
        
        # Common API endpoint patterns to try
        api_urls = [
            "https://www.olx.in/api/relevance/v2/search",
            "https://www.olx.in/api/relevance/v3/search",
            "https://mobile-api.olx.in/v1/search",
            "https://www.olx.in/ajax/search"
        ]
        
        for api_url in api_urls:
            try:
                params = {
                    'q': query,
                    'location': location,
                    'limit': limit,
                    'category': 'vehicles'
                }
                
                print(f"  → Trying: {api_url}")
                response = self.session.get(api_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if 'data' in data or 'results' in data or 'ads' in data:
                            print(f"  ✅ Found working API endpoint!")
                            return self.parse_api_response(data)
                    except json.JSONDecodeError:
                        continue
                
            except Exception as e:
                continue
        
        print("  ❌ No working API endpoints found")
        return []
    
    def parse_api_response(self, data):
        """Parse API response"""
        listings = []
        
        # Try different data structures
        items = data.get('data', data.get('results', data.get('ads', [])))
        
        for item in items:
            try:
                listing = {
                    'title': item.get('title', item.get('name', 'N/A')),
                    'price': item.get('price', item.get('amount', 'N/A')),
                    'location': item.get('location', item.get('city', 'N/A')),
                    'date': item.get('created_at', item.get('date', 'N/A')),
                    'link': item.get('url', item.get('link', 'N/A')),
                    'image_url': item.get('image', item.get('photo', 'N/A'))
                }
                listings.append(listing)
            except:
                continue
        
        return listings

# ============================================================================
# SOLUTION 3: PROXY-BASED SCRAPER
# ============================================================================

class ProxyBasedScraper:
    def __init__(self):
        self.proxies_list = []
        self.current_proxy_index = 0
        
    def get_free_proxies(self):
        """Get free proxy list"""
        print("🔄 Fetching free proxies...")
        
        try:
            # Free proxy sources
            proxy_urls = [
                "https://www.proxy-list.download/api/v1/get?type=http",
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
            ]
            
            for url in proxy_urls:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        proxies = response.text.strip().split('\n')
                        self.proxies_list.extend([p.strip() for p in proxies if ':' in p])
                except:
                    continue
            
            print(f"  ✅ Found {len(self.proxies_list)} proxies")
            return len(self.proxies_list) > 0
            
        except Exception as e:
            print(f"  ❌ Error fetching proxies: {e}")
            return False
    
    def get_next_proxy(self):
        """Get next proxy from list"""
        if not self.proxies_list:
            return None
        
        proxy = self.proxies_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies_list)
        
        return {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }
    
    def test_proxy(self, proxy):
        """Test if proxy is working"""
        try:
            response = requests.get(
                'http://httpbin.org/ip', 
                proxies=proxy, 
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def scrape_with_proxy_rotation(self, max_attempts=10):
        """Scrape using proxy rotation"""
        if not self.get_free_proxies():
            print("❌ No proxies available")
            return []
        
        for attempt in range(max_attempts):
            proxy = self.get_next_proxy()
            
            if not self.test_proxy(proxy):
                print(f"  ⚠ Proxy {proxy['http']} failed test")
                continue
            
            try:
                print(f"  → Trying proxy: {proxy['http']}")
                
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                response = session.get(
                    'https://www.olx.in/items/q-car-cover',
                    proxies=proxy,
                    timeout=15
                )
                
                if response.status_code == 200:
                    print(f"  ✅ Success with proxy: {proxy['http']}")
                    # Parse response here
                    return self.parse_html_response(response.text)
                
            except Exception as e:
                print(f"  ⚠ Proxy {proxy['http']} failed: {str(e)[:50]}")
                continue
        
        print("❌ All proxy attempts failed")
        return []
    
    def parse_html_response(self, html):
        """Parse HTML response"""
        # Use similar parsing logic as before
        soup = BeautifulSoup(html, 'html.parser')
        # ... parsing logic ...
        return []

# ============================================================================
# SOLUTION 4: ALTERNATIVE DATA SOURCES
# ============================================================================

class AlternativeDataSources:
    def __init__(self):
        self.session = requests.Session()
    
    def scrape_amazon_car_covers(self):
        """Scrape Amazon for car cover data (usually less protected)"""
        print("🛒 Searching Amazon for car covers...")
        
        try:
            url = "https://www.amazon.in/s?k=car+cover"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                products = soup.find_all('div', {'data-component-type': 's-search-result'})
                
                listings = []
                for product in products:
                    try:
                        title_elem = product.find('h2', class_='a-size-mini')
                        title = title_elem.get_text().strip() if title_elem else "N/A"
                        
                        price_elem = product.find('span', class_='a-price-whole')
                        price = f"₹{price_elem.get_text()}" if price_elem else "N/A"
                        
                        link_elem = product.find('h2').find('a') if product.find('h2') else None
                        link = f"https://amazon.in{link_elem['href']}" if link_elem else "N/A"
                        
                        listings.append({
                            'title': title,
                            'price': price,
                            'location': 'Amazon India',
                            'date': 'Available',
                            'link': link,
                            'image_url': 'N/A',
                            'source': 'Amazon'
                        })
                    except:
                        continue
                
                print(f"  ✅ Found {len(listings)} Amazon listings")
                return listings
                
        except Exception as e:
            print(f"  ❌ Amazon scraping failed: {e}")
        
        return []
    
    def scrape_flipkart_car_covers(self):
        """Scrape Flipkart for car cover data"""
        print("🛍️ Searching Flipkart for car covers...")
        
        try:
            url = "https://www.flipkart.com/search?q=car%20cover"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Flipkart parsing logic here
                print("  ✅ Flipkart connection successful")
                return []  # Implement parsing
                
        except Exception as e:
            print(f"  ❌ Flipkart scraping failed: {e}")
        
        return []

# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def main():
    print("🚗 Alternative Car Cover Data Collection Suite")
    print("=" * 60)
    
    all_listings = []
    
    # Method 1: Try Selenium
    print("\n🔧 METHOD 1: Selenium with Undetected Chrome")
    try:
        selenium_scraper = SeleniumOLXScraper()
        selenium_listings = selenium_scraper.scrape_with_selenium(max_pages=2)
        if selenium_listings:
            all_listings.extend(selenium_listings)
            print(f"✅ Selenium found {len(selenium_listings)} listings")
        else:
            print("❌ Selenium method failed")
    except Exception as e:
        print(f"❌ Selenium error: {e}")
    
    # Method 2: Try API approach
    print("\n🔧 METHOD 2: API-based approach")
    try:
        api_scraper = APIBasedScraper()
        api_listings = api_scraper.search_olx_api()
        if api_listings:
            all_listings.extend(api_listings)
            print(f"✅ API found {len(api_listings)} listings")
        else:
            print("❌ API method failed")
    except Exception as e:
        print(f"❌ API error: {e}")
    
    # Method 3: Try alternative sources
    print("\n🔧 METHOD 3: Alternative sources")
    try:
        alt_scraper = AlternativeDataSources()
        amazon_listings = alt_scraper.scrape_amazon_car_covers()
        if amazon_listings:
            all_listings.extend(amazon_listings)
            print(f"✅ Alternative sources found {len(amazon_listings)} listings")
    except Exception as e:
        print(f"❌ Alternative sources error: {e}")
    
    # Save results
    if all_listings:
        save_results(all_listings)
        print(f"\n🎉 SUCCESS! Total listings collected: {len(all_listings)}")
    else:
        print(f"\n❌ No listings found with any method")
        print("💡 Recommendations:")
        print("   • Try running at different times")
        print("   • Use a VPN service")
        print("   • Consider manual data collection")
        print("   • Look into paid proxy services")

def save_results(listings):
    """Save all collected listings"""
    # Save to CSV
    with open('alternative_car_covers.csv', 'w', newline='', encoding='utf-8-sig') as f:
        if listings:
            writer = csv.DictWriter(f, fieldnames=listings[0].keys())
            writer.writeheader()
            writer.writerows(listings)
    
    # Save to JSON
    with open('alternative_car_covers.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_listings': len(listings),
            'listings': listings
        }, f, indent=2, ensure_ascii=False)
    
    print("💾 Results saved to alternative_car_covers.csv and .json")

if __name__ == "__main__":
    main()