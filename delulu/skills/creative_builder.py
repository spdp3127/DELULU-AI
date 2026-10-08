import os
import re
import urllib.parse
import webbrowser
from typing import Dict, Any, Optional

def slugify(text: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9]+', '-', text.lower()).strip('-')
    return s or "project"

def build_website_html(topic: str, theme: str = "delulu_choice", tech_stack: str = "HTML5 / CSS3 / Vanilla JS", features: str = "") -> str:
    """
    Generates a complete, production-grade, responsive website
    with rich aesthetics, Google Fonts, glassmorphism, and working interactivity.
    """
    t_clean = topic.strip().title() if topic else "Modern Digital Experience"
    t_lower = topic.lower()

    # Determine niche category and customized color accents
    if any(k in t_lower for k in ["coffee", "cafe", "tea", "bakery", "roastery"]):
        category = "coffee"
        accent_color = "#f59e0b"
        accent_rgb = "245, 158, 11"
        accent_glow = "rgba(245, 158, 11, 0.35)"
        headline = f"Artisan Coffee & Craft Roasts"
        subhead = "Handcrafted organic brews, slow-poured to perfection with ethically sourced beans from across the globe."
        btn_cta = "Order Now"
        feature_1_title = "Single-Origin Beans"
        feature_1_desc = "Freshly roasted in small batches every sunrise to preserve peak flavor notes."
        feature_2_title = "Artisan Brewing"
        feature_2_desc = "Pour-over, AeroPress, and nitro cold brew crafted by certified master baristas."
        feature_3_title = "Sustainable Eco-Café"
        feature_3_desc = "100% biodegradable packaging, zero-waste kitchen, and fair-trade farm partnerships."
        item_1 = ("Caramel Velvet Cold Brew", "$6.50", "Steeped for 20 hours with Madagascar vanilla and sea-salt caramel cold foam.")
        item_2 = ("Signature Cortado", "$4.75", "Equal parts double espresso and silky steamed whole milk with latte art.")
        item_3 = ("Honeycomb Hazelnut Latte", "$5.90", "Espresso infused with roasted hazelnut butter and wildflower honey.")
        item_4 = ("Matcha Pistachio Cloud", "$6.20", "Ceremonial Japanese matcha topped with creamy pistachio sweet foam.")

    elif any(k in t_lower for k in ["gym", "fitness", "workout", "trainer", "crossfit", "bodybuilding"]):
        category = "fitness"
        accent_color = "#f43f5e"
        accent_rgb = "244, 63, 94"
        accent_glow = "rgba(244, 63, 94, 0.35)"
        headline = f"Forge Your Peak Strength & Physique"
        subhead = "Elite athletic training facilities, biometric-driven programming, and world-class certified coaching."
        btn_cta = "Claim Free Day Pass"
        feature_1_title = "Biometric Tracking"
        feature_1_desc = "Live heart-rate zones and recovery metrics synced directly with your mobile companion."
        feature_2_title = "Elite Equipment"
        feature_2_desc = "Olympic lifting platforms, Eleiko calibrated plates, and precision cardio machines."
        feature_3_title = "Expert Nutrition"
        feature_3_desc = "Customized meal blueprints and certified sports dietitian check-ins every month."
        item_1 = ("Starter Tier", "$49/mo", "Full gym floor access, locker rooms, and complimentary mobile workout tracking.")
        item_2 = ("Pro Athlete Tier", "$89/mo", "Unlimited group HIIT, sauna/ice bath recovery lounge, and 2 PT sessions/mo.")
        item_3 = ("VIP Elite Tier", "$149/mo", "Unlimited 1-on-1 coaching, biometric body composition scan, & nutrition plan.")
        item_4 = ("Day Access Pass", "$15", "Complete single-day all-access pass to gym floor, recovery suite, and classes.")

    elif any(k in t_lower for k in ["portfolio", "developer", "designer", "engineer", "resume", "personal"]):
        category = "portfolio"
        accent_color = "#00f0ff"
        accent_rgb = "0, 240, 255"
        accent_glow = "rgba(0, 240, 255, 0.35)"
        headline = f"Crafting Next-Gen Intelligent Digital Systems"
        subhead = "Full-stack software architect & creative technologist building high-performance AI-driven web applications."
        btn_cta = "Explore My Projects"
        feature_1_title = "Full-Stack Architecture"
        feature_1_desc = "Scalable microservices, real-time WebSocket sync, and sub-100ms API backends."
        feature_2_title = "AI & Agentic Systems"
        feature_2_desc = "Autonomous agent swarms, multimodal neural inference, and real-time voice orchestration."
        feature_3_title = "Fluid UI/UX Craft"
        feature_3_desc = "Glassmorphic cyber aesthetics, 60fps micro-animations, and accessible responsive design."
        item_1 = ("Autonomous AI Operating Layer", "Python & FastAPI", "Multi-tenant autonomous desktop assistant with zero-latency neural pipeline.")
        item_2 = ("Real-Time Crypto Telemetry", "TypeScript & Next.js", "High-frequency streaming financial dashboard with live order book visualizer.")
        item_3 = ("Spatial Web 3D Visualizer", "Three.js & WebGL", "Interactive 3D particle reactor core with physics-based reactive audio rendering.")
        item_4 = ("Cloud Neural Hub", "Go & Docker", "High-throughput edge computing mesh with automated container telemetry.")

    elif any(k in t_lower for k in ["car", "auto", "vehicle", "luxury car", "showroom"]):
        category = "automotive"
        accent_color = "#38bdf8"
        accent_rgb = "56, 189, 248"
        accent_glow = "rgba(56, 189, 248, 0.35)"
        headline = f"Precision Engineering Meets Pure Luxury"
        subhead = "Experience the pinnacle of automotive innovation, breathtaking aerodynamics, and handcrafted prestige."
        btn_cta = "Book a Private Test Drive"
        feature_1_title = "Hyper-Performance"
        feature_1_desc = "0-100 km/h in 2.4 seconds with active all-wheel torque vectoring."
        feature_2_title = "Aerodynamic Sculpt"
        feature_2_desc = "Carbon-fiber monocoque chassis tuned in European supersonic wind tunnels."
        feature_3_title = "Bespoke Interiors"
        feature_3_desc = "Hand-stitched Tuscan aniline leather with aircraft-grade aluminum accents."
        item_1 = ("Aero GT Hyper-Coupe", "$245,000", "780 HP Twin-Turbo V8 hybrid with active rear aerodynamic spoiler.")
        item_2 = ("Volt-E Super SUV", "$165,000", "Dual-motor electric powertrain with 650 km range and air-suspension.")
        item_3 = ("Monaco Roadster", "$210,000", "Retractable lightweight carbon hardtop with bespoke sports exhaust notes.")
        item_4 = ("Phantom Black Edition", "$290,000", "Matte obsidian finish with ceramic composite brakes and forged wheels.")

    else:
        category = "business"
        accent_color = "#00f0ff"
        accent_rgb = "0, 240, 255"
        accent_glow = "rgba(0, 240, 255, 0.35)"
        headline = f"Elevate Your Vision with {t_clean}"
        subhead = "State-of-the-art digital infrastructure engineered for performance, aesthetic brilliance, and seamless client delight."
        btn_cta = "Get Started Today"
        feature_1_title = "Intelligent Automation"
        feature_1_desc = "Autonomous workflows designed to save time and streamline end-to-end operations."
        feature_2_title = "Ultra-Fast Performance"
        feature_2_desc = "Optimized architecture delivering lightning-fast sub-second experiences globally."
        feature_3_title = "World-Class Design"
        feature_3_desc = "Modern glassmorphism, responsive fluidity, and curated visual excellence."
        item_1 = ("Starter Package", "$29/mo", "Essential features, automated backups, and 24/7 community assistance.")
        item_2 = ("Professional Suite", "$79/mo", "Full platform capabilities, dedicated infrastructure, and prioritized support.")
        item_3 = ("Enterprise Custom", "$199/mo", "Custom domain routing, bespoke security auditing, and dedicated engineer.")
        item_4 = ("Free Trial Pass", "$0", "14-day zero-risk trial with complete feature access and no credit card required.")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{t_clean} | Powered by DELULU AI</title>
  <meta name="description" content="Official website for {t_clean}, created and powered by DELULU AI.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #07090e;
      --bg-surface: rgba(18, 24, 38, 0.7);
      --bg-card: rgba(22, 30, 48, 0.65);
      --border: rgba(255, 255, 255, 0.1);
      --border-accent: rgba({accent_rgb}, 0.4);
      --acc: {accent_color};
      --acc-glow: {accent_glow};
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --radius: 16px;
      --font-main: 'Outfit', sans-serif;
      --font-display: 'Space Grotesk', sans-serif;
    }}

    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-family: var(--font-main);
    }}

    body {{
      background-color: var(--bg);
      color: var(--text);
      overflow-x: hidden;
      line-height: 1.6;
      background-image: 
        radial-gradient(circle at 15% 20%, rgba({accent_rgb}, 0.12) 0%, transparent 40%),
        radial-gradient(circle at 85% 65%, rgba({accent_rgb}, 0.08) 0%, transparent 45%);
      background-attachment: fixed;
    }}

    /* HEADER & NAV */
    header {{
      position: sticky;
      top: 0;
      z-index: 100;
      backdrop-filter: blur(20px);
      background: rgba(7, 9, 14, 0.85);
      border-bottom: 1px solid var(--border);
    }}

    .nav-container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 16px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .logo {{
      display: flex;
      align-items: center;
      gap: 10px;
      font-family: var(--font-display);
      font-size: 1.3rem;
      font-weight: 700;
      letter-spacing: -0.5px;
      color: #fff;
      text-decoration: none;
    }}

    .logo-badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: linear-gradient(135deg, var(--acc), rgba({accent_rgb}, 0.4));
      color: #000;
      font-weight: 800;
      font-size: 0.9rem;
    }}

    nav ul {{
      display: flex;
      list-style: none;
      gap: 28px;
      align-items: center;
    }}

    nav a {{
      color: var(--text-muted);
      text-decoration: none;
      font-weight: 500;
      font-size: 0.95rem;
      transition: color 0.2s ease;
    }}

    nav a:hover {{
      color: var(--acc);
    }}

    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 10px 22px;
      border-radius: 999px;
      font-weight: 600;
      font-size: 0.95rem;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      border: 1px solid transparent;
    }}

    .btn-primary {{
      background: var(--acc);
      color: #000;
      box-shadow: 0 0 24px var(--acc-glow);
    }}

    .btn-primary:hover {{
      transform: translateY(-2px);
      box-shadow: 0 0 32px rgba({accent_rgb}, 0.6);
    }}

    .btn-outline {{
      background: rgba(255, 255, 255, 0.05);
      border-color: var(--border);
      color: var(--text);
    }}

    .btn-outline:hover {{
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba({accent_rgb}, 0.5);
    }}

    /* HERO SECTION */
    .hero {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 90px 24px 60px;
      text-align: center;
    }}

    .hero-tag {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 16px;
      background: rgba({accent_rgb}, 0.1);
      border: 1px solid var(--border-accent);
      border-radius: 999px;
      color: var(--acc);
      font-size: 0.85rem;
      font-weight: 600;
      margin-bottom: 24px;
      letter-spacing: 0.5px;
    }}

    .hero h1 {{
      font-family: var(--font-display);
      font-size: clamp(2.5rem, 5vw, 4.2rem);
      font-weight: 800;
      line-height: 1.15;
      margin-bottom: 20px;
      letter-spacing: -1px;
    }}

    .hero h1 span {{
      background: linear-gradient(135deg, #fff 30%, var(--acc) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    .hero p {{
      max-width: 680px;
      margin: 0 auto 36px;
      font-size: 1.15rem;
      color: var(--text-muted);
    }}

    .hero-actions {{
      display: flex;
      justify-content: center;
      gap: 16px;
      flex-wrap: wrap;
    }}

    /* STATS STRIP */
    .stats-strip {{
      max-width: 1100px;
      margin: 40px auto 70px;
      padding: 24px;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      backdrop-filter: blur(16px);
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 24px;
      text-align: center;
    }}

    .stat-val {{
      font-family: var(--font-display);
      font-size: 2.2rem;
      font-weight: 700;
      color: var(--acc);
    }}

    .stat-label {{
      font-size: 0.88rem;
      color: var(--text-muted);
      margin-top: 4px;
    }}

    /* FEATURES GRID */
    .section-title {{
      text-align: center;
      margin-bottom: 48px;
    }}

    .section-title h2 {{
      font-family: var(--font-display);
      font-size: 2.2rem;
      font-weight: 700;
      margin-bottom: 12px;
    }}

    .section-title p {{
      color: var(--text-muted);
      font-size: 1rem;
    }}

    .features-grid {{
      max-width: 1200px;
      margin: 0 auto 90px;
      padding: 0 24px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 24px;
    }}

    .card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 32px;
      backdrop-filter: blur(16px);
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    .card:hover {{
      transform: translateY(-4px);
      border-color: var(--border-accent);
      box-shadow: 0 12px 36px rgba(0, 0, 0, 0.35);
    }}

    .card-icon {{
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: rgba({accent_rgb}, 0.15);
      color: var(--acc);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.4rem;
      margin-bottom: 20px;
    }}

    .card h3 {{
      font-size: 1.25rem;
      font-weight: 700;
      margin-bottom: 10px;
    }}

    .card p {{
      color: var(--text-muted);
      font-size: 0.95rem;
    }}

    /* INTERACTIVE SHOWCASE / MENU SECTION */
    .interactive-section {{
      max-width: 1200px;
      margin: 0 auto 100px;
      padding: 0 24px;
    }}

    .showcase-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 20px;
      margin-top: 32px;
    }}

    .item-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: all 0.25s ease;
    }}

    .item-card:hover {{
      border-color: var(--border-accent);
    }}

    .item-header {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 12px;
    }}

    .item-title {{
      font-weight: 700;
      font-size: 1.1rem;
    }}

    .item-price {{
      font-family: var(--font-display);
      font-weight: 700;
      color: var(--acc);
      font-size: 1.2rem;
    }}

    .item-desc {{
      color: var(--text-muted);
      font-size: 0.9rem;
      margin-bottom: 20px;
      flex-grow: 1;
    }}

    .item-btn {{
      width: 100%;
      padding: 10px;
      border-radius: 8px;
      background: rgba({accent_rgb}, 0.12);
      border: 1px solid var(--border-accent);
      color: #fff;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
    }}

    .item-btn:hover {{
      background: var(--acc);
      color: #000;
    }}

    /* CART & FEEDBACK TOAST */
    .toast {{
      position: fixed;
      bottom: 28px;
      right: 28px;
      background: #111827;
      border: 1px solid var(--acc);
      color: #fff;
      padding: 14px 24px;
      border-radius: 999px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
      display: none;
      align-items: center;
      gap: 10px;
      font-weight: 600;
      z-index: 1000;
    }}

    /* FOOTER */
    footer {{
      background: #040609;
      border-top: 1px solid var(--border);
      padding: 48px 24px;
      text-align: center;
      color: var(--text-muted);
      font-size: 0.9rem;
    }}

    footer a {{
      color: var(--acc);
      text-decoration: none;
    }}

    @media (max-width: 768px) {{
      nav ul {{ display: none; }}
      .hero {{ padding: 60px 16px 40px; }}
    }}
  </style>
</head>
<body>

  <!-- HEADER -->
  <header>
    <div class="nav-container">
      <a href="#" class="logo">
        <span class="logo-badge">✦</span>
        <span>{t_clean}</span>
      </a>
      <nav>
        <ul>
          <li><a href="#about">About</a></li>
          <li><a href="#features">Experience</a></li>
          <li><a href="#showcase">Offerings</a></li>
          <li><a href="#contact" class="btn btn-primary" onclick="openOrderModal()">{btn_cta}</a></li>
        </ul>
      </nav>
    </div>
  </header>

  <!-- MAIN HERO -->
  <main>
    <section class="hero" id="about">
      <div class="hero-tag">✨ DELULU AI GENERATIVE SUITE // CERTIFIED</div>
      <h1><span>{headline}</span></h1>
      <p>{subhead}</p>
      <div class="hero-actions">
        <button class="btn btn-primary" onclick="openOrderModal()">{btn_cta}</button>
        <a href="#showcase" class="btn btn-outline">Explore Selection</a>
      </div>
    </section>

    <!-- LIVE STATS STRIP -->
    <section class="stats-strip">
      <div>
        <div class="stat-val">100%</div>
        <div class="stat-label">Organic & Authentic</div>
      </div>
      <div>
        <div class="stat-val">4.9★</div>
        <div class="stat-label">Client Satisfaction</div>
      </div>
      <div>
        <div class="stat-val">24/7</div>
        <div class="stat-label">Instant Experience</div>
      </div>
      <div>
        <div class="stat-val">0s</div>
        <div class="stat-label">Wait Time Guarantee</div>
      </div>
    </section>

    <!-- FEATURES -->
    <section class="features-grid" id="features">
      <div class="card">
        <div class="card-icon">⚡</div>
        <h3>{feature_1_title}</h3>
        <p>{feature_1_desc}</p>
      </div>
      <div class="card">
        <div class="card-icon">💎</div>
        <h3>{feature_2_title}</h3>
        <p>{feature_2_desc}</p>
      </div>
      <div class="card">
        <div class="card-icon">🛡️</div>
        <h3>{feature_3_title}</h3>
        <p>{feature_3_desc}</p>
      </div>
    </section>

    <!-- SHOWCASE SELECTION -->
    <section class="interactive-section" id="showcase">
      <div class="section-title">
        <h2>Curated Offerings</h2>
        <p>Selected exclusively for your taste and refined expectations.</p>
      </div>

      <div class="showcase-grid">
        <div class="item-card">
          <div class="item-header">
            <span class="item-title">{item_1[0]}</span>
            <span class="item-price">{item_1[1]}</span>
          </div>
          <p class="item-desc">{item_1[2]}</p>
          <button class="item-btn" onclick="addToCart('{item_1[0]}')">Select</button>
        </div>

        <div class="item-card">
          <div class="item-header">
            <span class="item-title">{item_2[0]}</span>
            <span class="item-price">{item_2[1]}</span>
          </div>
          <p class="item-desc">{item_2[2]}</p>
          <button class="item-btn" onclick="addToCart('{item_2[0]}')">Select</button>
        </div>

        <div class="item-card">
          <div class="item-header">
            <span class="item-title">{item_3[0]}</span>
            <span class="item-price">{item_3[1]}</span>
          </div>
          <p class="item-desc">{item_3[2]}</p>
          <button class="item-btn" onclick="addToCart('{item_3[0]}')">Select</button>
        </div>

        <div class="item-card">
          <div class="item-header">
            <span class="item-title">{item_4[0]}</span>
            <span class="item-price">{item_4[1]}</span>
          </div>
          <p class="item-desc">{item_4[2]}</p>
          <button class="item-btn" onclick="addToCart('{item_4[0]}')">Select</button>
        </div>
      </div>
    </section>
  </main>

  <!-- INTERACTIVE TOAST -->
  <div class="toast" id="toast">
    <span>✓</span>
    <span id="toast-text">Selected item successfully!</span>
  </div>

  <!-- FOOTER -->
  <footer>
    <p>&copy; 2026 {t_clean}. All rights reserved.</p>
    <p style="margin-top: 8px;">Designed and synthesized with pride by <a href="https://github.com/spdp3127/DELULU-AI" target="_blank">DELULU AI Platform</a>.</p>
  </footer>

  <script>
    function addToCart(itemName) {{
      const toast = document.getElementById('toast');
      const text = document.getElementById('toast-text');
      text.textContent = 'Selected: ' + itemName + ' (Saved to order queue)';
      toast.style.display = 'flex';
      setTimeout(() => {{
        toast.style.display = 'none';
      }}, 3000);
    }}

    function openOrderModal() {{
      alert('Thank you for exploring {t_clean}! Your reservation/order portal is active.');
    }}
  </script>
</body>
</html>
"""
    return html

def save_and_open_website(topic: str, theme: str = "delulu_choice", tech_stack: str = "HTML5 / CSS3 / Vanilla JS", features: str = "") -> Dict[str, Any]:
    """
    Saves generated website to workspace/projects/<slug>/index.html
    and launches in default web browser.
    """
    clean_topic = topic.strip().title() if topic else "Modern Web App"
    slug = slugify(clean_topic)
    
    # Project directory
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    projects_dir = os.path.join(root_dir, "workspace", "projects", slug)
    os.makedirs(projects_dir, exist_ok=True)
    
    file_path = os.path.join(projects_dir, "index.html")
    html_code = build_website_html(clean_topic, theme=theme, tech_stack=tech_stack, features=features)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_code)
        
    abs_url = f"file:///{file_path.replace(os.sep, '/')}"
    try:
        webbrowser.open(abs_url)
    except Exception:
        pass
        
    return {
        "status": "success",
        "project_name": clean_topic,
        "slug": slug,
        "theme": "Cyber-Glass Modern Dark Mode" if theme in ["delulu_choice", "delulu_vinte_ishtam"] else theme,
        "tech_stack": tech_stack,
        "file_path": file_path,
        "preview_url": abs_url,
        "html_code": html_code
    }

def generate_svg_artwork(prompt: str, style: str = "delulu_choice") -> Dict[str, Any]:
    """Generates rich SVG visual vector composition and opens file."""
    clean_prompt = prompt.strip().title() if prompt else "Futuristic Vector Concept"
    slug = slugify(clean_prompt)
    
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    images_dir = os.path.join(root_dir, "workspace", "images")
    os.makedirs(images_dir, exist_ok=True)
    file_path = os.path.join(images_dir, f"{slug}.svg")
    
    svg_code = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#07090e"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <radialGradient id="cyberGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#00f0ff" stop-opacity="0.8"/>
      <stop offset="60%" stop-color="#a855f7" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="#000" stop-opacity="0"/>
    </radialGradient>
    <filter id="neonBlur" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="12" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="800" height="600" fill="url(#bgGrad)"/>
  
  <!-- Cyber Glow Core -->
  <circle cx="400" cy="270" r="180" fill="url(#cyberGlow)"/>
  
  <!-- Geometry Rings -->
  <circle cx="400" cy="270" r="140" fill="none" stroke="#00f0ff" stroke-width="2" stroke-dasharray="12 6" opacity="0.8"/>
  <circle cx="400" cy="270" r="100" fill="none" stroke="#a855f7" stroke-width="2.5" opacity="0.9" filter="url(#neonBlur)"/>
  <circle cx="400" cy="270" r="50" fill="#00f0ff" opacity="0.9" filter="url(#neonBlur)"/>
  
  <!-- Typography Badge -->
  <text x="400" y="470" font-family="'Space Grotesk', sans-serif" font-size="28" font-weight="bold" fill="#ffffff" text-anchor="middle" letter-spacing="1">
    {clean_prompt}
  </text>
  <text x="400" y="505" font-family="'Outfit', sans-serif" font-size="16" fill="#94a3b8" text-anchor="middle">
    Synthesized with DELULU AI Visual Engine
  </text>
</svg>"""

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(svg_code)

    abs_url = f"file:///{file_path.replace(os.sep, '/')}"
    try:
        webbrowser.open(abs_url)
    except Exception:
        pass

    return {
        "status": "success",
        "title": clean_prompt,
        "file_path": file_path,
        "preview_url": abs_url,
        "svg_code": svg_code
    }
