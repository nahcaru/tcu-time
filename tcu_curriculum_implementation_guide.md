# TCU Curriculum Code Fetcher - Implementation Guide

## Summary

Successfully fetched and analyzed TCU's graduate school curriculum codes from:
**URL:** `https://websrv.tcu.ac.jp/tcu_web_v3/slbsscmr.do`

### Key Findings

✅ **No form submission required** - All codes visible on initial page load  
✅ **Legacy TLS works** - TLSv1.2 connection successful with `verify=False`  
✅ **Simple HTML structure** - Standard `<table>` with `<a>` links  
✅ **Stable format** - Code pattern consistent since 2011  

---

## Quick Implementation for enricher.py

```python
def fetch_curriculum_codes():
    """
    Fetch graduate school curriculum codes from TCU syllabus system
    
    Returns:
        dict: {code: name} mapping for master's (sm*) and doctoral (sd*) programs
        
    Example:
        {
            'sm260101': '2026年度 機械専攻(機械工学)',
            'sd260101': '2026年度 博士後期機械専攻',
            ...
        }
    """
    import requests
    import re
    from urllib3 import disable_warnings
    from urllib3.exceptions import InsecureRequestWarning
    
    # Suppress SSL warnings for legacy TLS
    disable_warnings(InsecureRequestWarning)
    
    url = "https://websrv.tcu.ac.jp/tcu_web_v3/slbsscmr.do"
    
    try:
        # Fetch with legacy TLS support
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
        
        # Parse curriculum codes (main entries only, not subcategories)
        pattern = re.compile(r'value\(crclm\)=(s[md]\d{6})&buttonName[^>]*>([^<]+)<')
        matches = pattern.findall(response.text)
        
        # Build dictionary - filter graduate school codes only
        curriculum_codes = {}
        for code, name in matches:
            if code.startswith(('sm', 'sd')) and code not in curriculum_codes:
                curriculum_codes[code] = name.strip()
        
        return curriculum_codes
        
    except Exception as e:
        print(f"Warning: Could not fetch curriculum codes: {e}")
        return {}


# Usage Example
if __name__ == "__main__":
    codes = fetch_curriculum_codes()
    print(f"Fetched {len(codes)} curriculum codes")
    
    # Show 2026 master's programs
    masters_2026 = {k: v for k, v in codes.items() if k.startswith('sm26')}
    for code, name in sorted(masters_2026.items()):
        print(f"{code}: {name}")
```

---

## Curriculum Code Format

### Master's Programs (修士課程)
**Pattern:** `sm{YY}{MM}{NN}`

- `sm` = Master's prefix
- `YY` = Year (2-digit: 26=2026, 25=2025, etc.)
- `MM` = Major code
  - `01` = 機械 (Mechanical)
  - `03` = 電気電子 (Electrical/Electronic)
  - `05` = 情報 (Information)
  - `07` = 建築 (Architecture)
  - `09` = 化学 (Chemistry)
  - `10` = 共同原子力 (Joint Nuclear)
  - `11` = 自然科学 (Natural Science)
- `NN` = Subtype
  - `01` = Main track
  - `02` = Alternative track (e.g., system variant)

**Example:** `sm260101` → 2026年度 機械専攻(機械工学)

### Doctoral Programs (博士後期課程)
**Pattern:** `sd{YY}{MM}01`

- `sd` = Doctoral prefix
- `YY` = Year (2-digit)
- `MM` = Major code
  - `01` = 機械 (Mechanical)
  - `03` = 電気・化学 (Electrical & Chemistry)
  - `07` = 建築都市デザイン (Architecture & Urban Design)
  - `09` = 情報 (Information)
  - `11` = 自然科学 (Natural Science)
- Always ends with `01`

**Example:** `sd260101` → 2026年度 博士後期機械専攻

---

## 2026 Graduate School Codes (Current)

### Master's Programs (12 programs)
```
sm260101: 2026年度 機械専攻(機械工学)
sm260201: 2026年度 機械専攻(機械システム工学)
sm260301: 2026年度 電気・化学専攻(電気電子工学)
sm260401: 2026年度 電気・化学専攻(医用工学)
sm260501: 2026年度 電気・化学専攻(応用化学)
sm260601: 2026年度 共同原子力専攻(共同原子力)
sm260602: 2026年度 共同原子力専攻(共同原子力・早稲田)
sm260701: 2026年度 建築都市デザイン専攻(建築学)
sm260801: 2026年度 建築都市デザイン専攻(都市工学)
sm260901: 2026年度 情報専攻(情報工学)
sm261001: 2026年度 情報専攻(システム情報工学)
sm261101: 2026年度 自然科学専攻(自然科学)
```

### Doctoral Programs (5 programs)
```
sd260101: 2026年度 博士後期機械専攻
sd260301: 2026年度 博士後期電気・化学専攻
sd260701: 2026年度 博士後期建築都市デザイン専攻
sd260901: 2026年度 博士後期情報専攻
sd261101: 2026年度 博士後期自然科学専攻
```

---

## HTML Structure

Each curriculum entry follows this pattern:

```html
<tr class="column_odd">  <!-- or column_even -->
  <td width="32%">
    <a href="/tcu_web_v3/slbsscmr.do?value(nendo)=2025&value(crclm)=sm260101&buttonName=searchKougi&methodname=crclmSearch">
      2026年度 機械専攻(機械工学)
    </a>
  </td>
  <td>
    <!-- Subcategories (not needed for main code extraction) -->
    <a href="...&value(bunya)=zs2013...">■授業科目■</a><br>
    <a href="...&value(bunya)=zs2014...">■実習・演習■</a><br>
    <a href="...&value(bunya)=zs2015...">■特別研究■</a><br>
  </td>
</tr>
```

**Key elements:**
- Curriculum code in `value(crclm)=CODE` parameter
- Name in link text
- `buttonName=searchKougi` indicates main curriculum link (not subcategory)

---

## Parsing Strategy

### Regex Approach (Recommended)
```python
pattern = re.compile(r'value\(crclm\)=(s[md]\d{6})&buttonName[^>]*>([^<]+)<')
matches = pattern.findall(html_text)
# Returns: [('sm260101', '2026年度 機械専攻(機械工学)'), ...]
```

### BeautifulSoup Approach (Alternative)
```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html_text, 'html.parser')
curriculum_codes = {}

for link in soup.find_all('a', href=True):
    href = link['href']
    if 'value(crclm)=' in href and 'buttonName=searchKougi' in href:
        match = re.search(r'value\(crclm\)=([^&]+)', href)
        if match:
            code = match.group(1)
            if code.startswith(('sm', 'sd')):
                curriculum_codes[code] = link.get_text(strip=True)
```

---

## Error Handling

### Common Issues

1. **SSLError / Certificate verification failed**
   - **Solution:** Use `verify=False` in requests
   - **Note:** This is safe for read-only public data

2. **Timeout**
   - **Solution:** Set `timeout=10` or higher
   - **Fallback:** Use cached codes from JSON

3. **Connection refused**
   - **Solution:** Check if university server is accessible
   - **Fallback:** Use local JSON file

### Recommended Implementation with Fallback

```python
def fetch_curriculum_codes():
    try:
        # Try fetching from web
        response = requests.get(URL, verify=False, timeout=10)
        response.raise_for_status()
        codes = parse_curriculum_codes(response.text)
        
        # Cache for future use
        if codes:
            save_to_cache(codes)
            return codes
    except Exception as e:
        logger.warning(f"Failed to fetch curriculum codes: {e}")
    
    # Fallback to cached/bundled data
    return load_from_cache()
```

---

## Data Files Provided

1. **tcu_curriculum_analysis.txt**  
   - Full analysis document
   - HTML structure details
   - Implementation notes

2. **tcu_grad_curriculum_codes.json**  
   - All 263 graduate school curriculum codes (2011-2026)
   - Ready-to-use JSON format
   - Can be bundled with enricher.py as fallback

3. **tcu_curriculum_implementation_guide.md** (this file)  
   - Quick reference for implementation
   - Code examples
   - Current year codes

---

## Statistics

- **Total codes:** 263 (all years 2011-2026)
- **Master's programs:** 198 codes
- **Doctoral programs:** 65 codes
- **2026 programs:** 17 codes (12 master's + 5 doctoral)
- **Historical data:** Goes back to 2011 for master's, 2016 for doctoral

---

## Next Steps for Implementation

1. Add `fetch_curriculum_codes()` to `enricher.py`
2. Import dependencies: `requests`, `re`, `urllib3`
3. Bundle `tcu_grad_curriculum_codes.json` as fallback
4. Add error handling with cache fallback
5. Test with sample curriculum codes (e.g., `sm260101`)

---

## Testing

```python
# Test the function
codes = fetch_curriculum_codes()
assert len(codes) > 0, "No codes fetched"
assert 'sm260101' in codes, "Missing current master's code"
assert 'sd260101' in codes, "Missing current doctoral code"
print(f"✅ Successfully fetched {len(codes)} curriculum codes")
```

---

## Questions?

Refer to:
- `tcu_curriculum_analysis.txt` for detailed HTML structure
- `tcu_grad_curriculum_codes.json` for complete code list
- TCU syllabus page: https://websrv.tcu.ac.jp/tcu_web_v3/slbsscmr.do
