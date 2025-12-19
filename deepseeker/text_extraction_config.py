"""
Text Extraction Configuration
Defines patterns and settings for cleaning HTML content
"""

# Common noise patterns to remove from extracted text
# These patterns match common website navigation, ads, and boilerplate text
REMOVAL_PATTERNS = [
    # Navigation and site structure
    r'导航\s*：?\s*[\w\s]*',
    r'首页|主页|关于|联系我们|隐私政策|服务条款|用户协议',
    r'导航栏|菜单|目录|站点地图',
    
    # Copyright and legal
    r'Copyright|版权所有|©\s*\d{4}',
    r'All rights reserved',
    r'保留所有权利',
    
    # UI elements
    r'返回顶部|回到顶部|Back to top',
    r'展开|收起|折叠',
    r'加载更多|查看更多|阅读更多',
    
    # Social and sharing
    r'分享到：?\s*(微信|微博|QQ|Facebook|Twitter|LinkedIn|Reddit)',
    r'分享|转发|收藏|点赞',
    
    # Calls to action and ads
    r'广告|推广|赞助|优惠|折扣|促销',
    r'立即报名|立即购买|立即下载|点击这里',
    r'了解更多|查看详情|阅读原文',
    
    # User actions
    r'登录|注册|Sign in|Sign up|Log in|Logout',
    r'用户名|密码|邮箱|手机号',
    
    # Search and filtering
    r'搜索：?\s*[\w\s]*',
    r'搜索|查找|筛选|过滤',
    
    # Recommendations and related content
    r'热门推荐|相关阅读|猜你喜欢|推荐阅读',
    r'你可能还喜欢|其他人也在看',
    
    # Comments and engagement
    r'评论|留言|回复|点赞数|阅读量',
    r'发表评论|我要评论',
    
    # Meta information (often redundant in extracted content)
    r'发布时间：?\s*[\d\-:\s]*',
    r'更新时间：?\s*[\d\-:\s]*',
    r'作者：?\s*[\w\s]*',
    r'阅读时间：?\s*[\w\s]*',
    r'Published:\s*[\d\-:\s]*',
    r'Updated:\s*[\d\-:\s]*',
    r'Author:\s*[\w\s]*',
    r'Read time:\s*[\w\s]*',
    
    # Common footer patterns
    r'技术支持|技术支持：?\s*[\w\s]*',
    r'备案号：?\s*[\w\s]*',
    r'ICP备',    r'Contact:\s*[\w\s@.]*',
    r'联系方式：?\s*[\w\s@.]*',    
    # Common Chinese patterns
    r'当前位置|面包屑',
    r'上一篇|下一篇',
    r'相关文章|热门文章',
    r'最新文章|最新发布',
]

# Tags whose content should be prioritized during extraction
IMPORTANT_TAGS = [
    'p',      # Paragraphs
    'h1',     # Main headings
    'h2',     # Section headings
    'h3',     # Subsection headings
    'h4',     # Minor headings
    'h5',     # Minor headings
    'h6',     # Minor headings
    'li',     # List items
    'blockquote',  # Quotes
    'article',     # Article content
    'section',     # Sections
    'pre',         # Preformatted text (often code)
    'code',        # Code snippets
]

# Tags that contain meaningful content (for fallback extraction)
CONTENT_TAGS = [
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'li', 'blockquote', 'article', 'section',
    'pre', 'code', 'span', 'div', 'strong', 'em'
]

# Minimum length for extracted content to be considered relevant
# If extracted content is shorter than this, fall back to full extraction
MIN_RELEVANT_LENGTH = 50

# Maximum length for extracted text (default)
DEFAULT_MAX_LENGTH = 8000

# Quality thresholds
RELEVANCE_THRESHOLD_HIGH = 0.7
RELEVANCE_THRESHOLD_MEDIUM = 0.4
RELEVANCE_THRESHOLD_LOW = 0.1