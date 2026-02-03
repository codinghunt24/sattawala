import streamlit as st

st.set_page_config(
    page_title="My Website",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Remove all default padding and margins */
    .stApp {
        background: white !important;
    }
    
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
        margin: 0 !important;
    }
    
    .stMainBlockContainer {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    
    .stApp > header {
        display: none !important;
    }
    
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    div[data-testid="stAppViewBlockContainer"] {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    
    /* Base responsive container */
    .responsive-container {
        width: 100%;
        max-width: 1200px;
        margin: 0 auto;
        padding-left: 20px;
        padding-right: 20px;
        box-sizing: border-box;
    }
    
    /* Logo section */
    .logo-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px 0;
        text-align: center;
    }
    
    .logo-container {
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    .logo {
        width: 80px;
        height: 80px;
        background: white;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 40px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    .logo-text {
        color: white;
        font-size: 28px;
        font-weight: bold;
        margin-top: 15px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    /* Navigation Menu */
    .nav-section {
        background: #2c3e50;
        padding: 0;
        position: sticky;
        top: 0;
        z-index: 1000;
    }
    
    .nav-menu {
        display: flex;
        justify-content: center;
        align-items: center;
        flex-wrap: wrap;
        gap: 5px;
        padding: 15px 20px;
    }
    
    .nav-item {
        color: white;
        text-decoration: none;
        padding: 12px 25px;
        border-radius: 5px;
        transition: all 0.3s ease;
        font-weight: 500;
        cursor: pointer;
    }
    
    .nav-item:hover {
        background: #3498db;
        transform: translateY(-2px);
    }
    
    .nav-item.active {
        background: #3498db;
    }
    
    /* Header section */
    .header-section {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 30px 0;
        text-align: center;
    }
    
    .header-title {
        font-size: 42px;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 15px;
    }
    
    .header-subtitle {
        font-size: 18px;
        color: #7f8c8d;
        max-width: 600px;
        margin: 0 auto;
        line-height: 1.6;
    }
    
    /* Content area */
    .content-section {
        background: #ffffff;
        padding: 80px 0;
        min-height: 400px;
    }
    
    .content-placeholder {
        text-align: center;
        color: #bdc3c7;
        font-size: 18px;
        padding: 100px 20px;
        border: 2px dashed #ecf0f1;
        border-radius: 10px;
        background: #fafafa;
    }
    
    /* Footer navigation */
    .footer-nav-section {
        background: #34495e;
        padding: 40px 0;
    }
    
    .footer-nav {
        display: flex;
        justify-content: center;
        align-items: center;
        flex-wrap: wrap;
        gap: 20px;
    }
    
    .footer-nav-item {
        color: #bdc3c7;
        text-decoration: none;
        padding: 10px 20px;
        transition: color 0.3s ease;
        cursor: pointer;
    }
    
    .footer-nav-item:hover {
        color: white;
    }
    
    /* Footer copyright */
    .footer-section {
        background: #2c3e50;
        padding: 25px 0;
        text-align: center;
    }
    
    .copyright-text {
        color: #95a5a6;
        font-size: 14px;
    }
    
    /* Responsive styles for tablets */
    @media (max-width: 768px) {
        .responsive-container {
            padding-left: 15px;
            padding-right: 15px;
        }
        
        .logo {
            width: 60px;
            height: 60px;
            font-size: 30px;
        }
        
        .logo-text {
            font-size: 22px;
        }
        
        .nav-menu {
            gap: 3px;
            padding: 10px 15px;
        }
        
        .nav-item {
            padding: 10px 15px;
            font-size: 14px;
        }
        
        .header-title {
            font-size: 32px;
        }
        
        .header-subtitle {
            font-size: 16px;
            padding: 0 15px;
        }
        
        .content-section {
            padding: 50px 0;
            min-height: 300px;
        }
        
        .footer-nav {
            gap: 10px;
        }
        
        .footer-nav-item {
            padding: 8px 15px;
            font-size: 14px;
        }
    }
    
    /* Responsive styles for mobile */
    @media (max-width: 480px) {
        .responsive-container {
            padding-left: 10px;
            padding-right: 10px;
        }
        
        .logo-section {
            padding: 20px 0;
        }
        
        .logo {
            width: 50px;
            height: 50px;
            font-size: 25px;
        }
        
        .logo-text {
            font-size: 18px;
        }
        
        .nav-menu {
            flex-direction: row;
            gap: 3px;
            padding: 10px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .nav-item {
            padding: 8px 10px;
            font-size: 12px;
        }
        
        .header-section {
            padding: 20px 0;
        }
        
        .header-title {
            font-size: 26px;
        }
        
        .header-subtitle {
            font-size: 14px;
        }
        
        .content-section {
            padding: 40px 0;
            min-height: 250px;
        }
        
        .content-placeholder {
            padding: 60px 15px;
            font-size: 16px;
        }
        
        .footer-nav {
            flex-direction: row;
            flex-wrap: wrap;
            justify-content: center;
            gap: 5px;
        }
        
        .footer-nav-item {
            padding: 8px 10px;
            font-size: 12px;
        }
        
        .footer-section {
            padding: 20px 0;
        }
        
        .copyright-text {
            font-size: 12px;
            padding: 0 10px;
        }
    }
</style>
""", unsafe_allow_html=True)

# Logo Section
st.markdown("""
<div class="logo-section">
    <div class="responsive-container">
        <div class="logo-container">
            <div class="logo">🌐</div>
        </div>
        <div class="logo-text">My Website</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Navigation Menu
st.markdown("""
<div class="nav-section">
    <div class="responsive-container">
        <div class="nav-menu">
            <span class="nav-item active">Home</span>
            <span class="nav-item">About</span>
            <span class="nav-item">Services</span>
            <span class="nav-item">Contact</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Header Section
st.markdown("""
<div class="header-section">
    <div class="responsive-container">
        <div class="header-title">Welcome to Our Website</div>
        <div class="header-subtitle">
            This is a beautiful responsive website built with Python. 
            Explore our services and discover what we can do for you.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Content Area (Blank)
st.markdown("""
<div class="content-section">
    <div class="responsive-container">
        <div class="content-placeholder">
            Content Area - Ready for future content
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Footer Navigation
st.markdown("""
<div class="footer-nav-section">
    <div class="responsive-container">
        <div class="footer-nav">
            <span class="footer-nav-item">Home</span>
            <span class="footer-nav-item">About</span>
            <span class="footer-nav-item">Services</span>
            <span class="footer-nav-item">Contact</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Footer Copyright
st.markdown("""
<div class="footer-section">
    <div class="responsive-container">
        <div class="copyright-text">
            © 2026 My Website. All rights reserved. | Designed with ❤️ in Python
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
