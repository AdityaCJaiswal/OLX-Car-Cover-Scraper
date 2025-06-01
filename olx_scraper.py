#!/usr/bin/env python3
"""
OLX Car Cover Scraper
Scrapes car cover listings from OLX India and saves results to a CSV file.
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import random
from urllib.parse import urljoin
import sys

class OLXScraper:
    def __init__(self):
        self.base_url = "https://www.olx.in"
        self.search_url = "https://www.olx.in/items/q-car-cover"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_page_content(self, url, max_retries=3):
        """Fetch page content with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(2, 5))
                else:
                    raise
    
    def parse_listing(self, listing_element):
        """Extract data from a single listing element"""
        try:
            # Title
            title_elem = listing_element.find('span', {'data-aut-id': 'itemTitle'})
            title = title_elem.get_text(strip=True) if title_elem else "N/A"
            
            # Price
            price_elem = listing_element.find('span', {'data-aut-id': 'itemPrice'})
            price = price_elem.get_text(strip=True) if price_elem else "N/A"
            
            # Location
            location_elem = listing_element.find('span', {'data-aut-id': 'item-location'})
            location = location_elem.get_text(strip=True) if location_elem else "N/A"
            
            # Date
            date_elem = listing_element.find('span', {'data-aut-id': 'item-date'})
            date = date_elem.get_text(strip=True) if date_elem else "N/A"
            
            # Link
            link_elem = listing_element.find('a', href=True)
            link = urljoin(self.base_url, link_elem['href']) if link_elem else "N/A"
            
            # Image
            img_elem = listing_element.find('img')
            image_url = img_elem.get('src') or img_elem.get('data-src') if img_elem else "N/A"
            
            return {
                'title': title,
                'price': price,
                'location': location,
                'date': date,
                'link': link,
                'image_url': image_url
            }
        except Exception as e:
            print(f"Error parsing listing: {e}")
            return None
    
    def scrape_listings(self, max_pages=5):
        """Scrape car cover listings from OLX"""
        all_listings = []
        
        for page in range(1, max_pages + 1):
            print(f"Scraping page {page}...")
            
            # Construct URL for current page
            if page == 1:
                url = self.search_url
            else:
                url = f"{self.search_url}?page={page}"
            
            try:
                html_content = self.get_page_content(url)
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find all listing containers
                listings = soup.find_all('div', {'data-aut-id': 'itemBox'})
                
                if not listings:
                    print(f"No listings found on page {page}. Trying alternative selectors...")
                    # Try alternative selectors
                    listings = soup.find_all('div', class_='_1AtVbE')
                    if not listings:
                        listings = soup.find_all('div', class_='_2tW1d5')
                
                if not listings:
                    print(f"No listings found on page {page}. Stopping.")
                    break
                
                page_listings = []
                for listing in listings:
                    parsed_listing = self.parse_listing(listing)
                    if parsed_listing and parsed_listing['title'] != "N/A":
                        page_listings.append(parsed_listing)
                
                all_listings.extend(page_listings)
                print(f"Found {len(page_listings)} listings on page {page}")
                
                # Add delay between requests
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"Error scraping page {page}: {e}")
                continue
        
        return all_listings
    
    def save_to_csv(self, listings, filename='olx_car_covers.csv'):
        """Save listings to CSV file"""
        if not listings:
            print("No listings to save.")
            return
        
        fieldnames = ['title', 'price', 'location', 'date', 'link', 'image_url']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(listings)
        
        print(f"Saved {len(listings)} listings to {filename}")
    
    def save_to_json(self, listings, filename='olx_car_covers.json'):
        """Save listings to JSON file"""
        if not listings:
            print("No listings to save.")
            return
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(listings, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(listings)} listings to {filename}")

def main():
    """Main function to run the scraper"""
    print("OLX Car Cover Scraper Starting...")
    print("=" * 50)
    
    scraper = OLXScraper()
    
    try:
        # Scrape listings
        listings = scraper.scrape_listings(max_pages=3)
        
        if listings:
            print(f"\nTotal listings found: {len(listings)}")
            print("=" * 50)
            
            # Save to both CSV and JSON
            scraper.save_to_csv(listings)
            scraper.save_to_json(listings)
            
            # Display first few listings
            print("\nFirst 5 listings:")
            for i, listing in enumerate(listings[:5], 1):
                print(f"{i}. {listing['title']}")
                print(f"   Price: {listing['price']}")
                print(f"   Location: {listing['location']}")
                print(f"   Date: {listing['date']}")
                print(f"   Link: {listing['link']}")
                print()
        else:
            print("No listings found. The website structure might have changed.")
            
    except KeyboardInterrupt:
        print("\nScraping interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
