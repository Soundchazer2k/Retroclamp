# LLM GUI Screenshot Evaluation Instruction Set
## Complete Guide for Analyzing User Interface Screenshots Using Nielsen's Usability Heuristics

### Overview
This instruction set enables an LLM coding assistant to systematically evaluate GUI screenshots based on Nielsen's 10 Usability Heuristics. Each heuristic includes detailed evaluation criteria, visual detection methods, and example analysis prompts.

---

## 1. Visibility of System Status

### **Definition**
The system should always keep users informed about what's happening through appropriate feedback within reasonable time.

### **Evaluation Criteria**
- **Loading Indicators**: Progress bars, spinners, or percentage indicators during operations
- **Status Messages**: Confirmation messages, notifications, or alerts
- **Visual Feedback**: Button states (pressed, hover, disabled), form validation indicators
- **Current State**: Breadcrumbs, active page indicators, selected items
- **System Response**: Immediate visual response to user actions

### **Computer Vision Detection Methods**
```python
# Example: Detect loading indicators
import cv2
import numpy as np

def detect_loading_indicators(screenshot):
    # Convert to grayscale
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    # Detect circular progress indicators (spinners)
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 20,
                              param1=50, param2=30, minRadius=10, maxRadius=50)

    # Detect rectangular progress bars using edge detection
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    progress_bars = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h
        if 3 < aspect_ratio < 10 and 100 < w < 400:  # Typical progress bar dimensions
            progress_bars.append((x, y, w, h))

    return circles, progress_bars
```

### **Analysis Prompt Template**
```
Analyze the provided screenshot for system status visibility:

1. **Loading States**: Are there visible loading indicators (progress bars, spinners) for long operations?
2. **Feedback Mechanisms**: Do interactive elements provide immediate visual feedback when clicked/tapped?
3. **Status Communication**: Are important system states (error, success, processing) clearly communicated?
4. **Current Location**: Can users easily determine where they are in the system?
5. **Action Confirmation**: Are user actions acknowledged with appropriate visual responses?

Rate visibility of system status: [Excellent/Good/Fair/Poor]
Provide specific examples and suggest improvements.
```

---

## 2. Match Between System and Real World

### **Definition**
The system should use familiar language, concepts, and conventions that users encounter in the real world.

### **Evaluation Criteria**
- **Familiar Icons**: Use of universally recognized symbols (trash can for delete, magnifying glass for search)
- **Natural Language**: Plain language instead of technical jargon
- **Real-world Metaphors**: Folder icons for directories, shopping cart for e-commerce
- **Logical Information Architecture**: Information organized in expected hierarchies
- **Cultural Conventions**: Appropriate use of colors, symbols, and layouts for target audience

### **Computer Vision Detection Methods**
```python
# Example: Detect and classify common UI icons
import cv2
from sklearn.cluster import KMeans

def analyze_icon_familiarity(screenshot):
    # Extract small square regions (potential icons)
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    # Detect corners and small rectangular regions
    corners = cv2.goodFeaturesToTrack(gray, 100, 0.01, 10)

    # Template matching for common icons
    templates = {
        'search': cv2.imread('search_icon_template.png', 0),
        'delete': cv2.imread('delete_icon_template.png', 0),
        'home': cv2.imread('home_icon_template.png', 0),
        'settings': cv2.imread('settings_icon_template.png', 0)
    }

    recognized_icons = []
    for name, template in templates.items():
        result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= 0.8)
        for pt in zip(*locations[::-1]):
            recognized_icons.append((name, pt))

    return recognized_icons
```

### **Analysis Prompt Template**
```
Evaluate how well the interface matches real-world conventions:

1. **Icon Recognition**: Are icons universally recognizable (search, delete, home, settings)?
2. **Language Clarity**: Is the text in plain language rather than technical jargon?
3. **Metaphor Usage**: Are real-world metaphors used appropriately (folders, trash, shopping cart)?
4. **Navigation Logic**: Does the information architecture follow expected patterns?
5. **Cultural Appropriateness**: Are colors, symbols, and layouts appropriate for the target audience?

Rate real-world matching: [Excellent/Good/Fair/Poor]
Identify specific examples and suggest improvements.
```

---

## 3. User Control and Freedom

### **Definition**
Users should have control over the interface and easy ways to exit unwanted states.

### **Evaluation Criteria**
- **Undo/Redo Functionality**: Clear undo and redo options for reversible actions
- **Navigation Control**: Back buttons, breadcrumbs, or clear navigation paths
- **Exit Options**: Clear ways to cancel operations or exit dialogs
- **User Pace**: Users can control the pace of interactions
- **Customization**: Users can customize interface elements when appropriate

### **Computer Vision Detection Methods**
```python
# Example: Detect undo/redo and navigation controls
def detect_control_elements(screenshot):
    # OCR to find text-based controls
    import pytesseract

    # Extract text from screenshot
    text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)

    # Look for control-related keywords
    control_keywords = ['undo', 'redo', 'back', 'cancel', 'exit', 'close', 'previous', 'next']
    found_controls = []

    for i, word in enumerate(text_data['text']):
        if word.lower() in control_keywords:
            x, y, w, h = (text_data['left'][i], text_data['top'][i],
                         text_data['width'][i], text_data['height'][i])
            found_controls.append({
                'type': word.lower(),
                'location': (x, y, w, h),
                'confidence': text_data['conf'][i]
            })

    # Detect common UI control patterns (X buttons, arrow buttons)
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    # Detect X-shaped close buttons
    # ... (implementation for detecting X patterns)

    return found_controls
```

### **Analysis Prompt Template**
```
Assess user control and freedom in the interface:

1. **Undo/Redo**: Are there clear options to undo or redo actions?
2. **Navigation**: Can users easily navigate back or exit current states?
3. **Cancel Operations**: Are there clear ways to cancel ongoing operations?
4. **User Pace**: Can users control the timing and pace of interactions?
5. **Escape Routes**: Are there obvious ways to exit dialogs or unwanted states?

Rate user control: [Excellent/Good/Fair/Poor]
Provide specific examples and recommendations.
```

---

## 4. Consistency and Standards

### **Definition**
The interface should follow established conventions and maintain internal consistency.

### **Evaluation Criteria**
- **Visual Consistency**: Consistent use of colors, fonts, and spacing
- **Interaction Patterns**: Similar elements behave similarly throughout
- **Terminology**: Consistent language and labeling across the interface
- **Layout Patterns**: Similar functions appear in similar locations
- **Platform Conventions**: Adherence to platform-specific guidelines (iOS, Android, Web)

### **Computer Vision Detection Methods**
```python
# Example: Analyze visual consistency
def analyze_consistency(screenshot):
    # Color palette analysis
    from sklearn.cluster import KMeans
    import numpy as np

    # Reshape image data
    data = screenshot.reshape((-1, 3))

    # Find dominant colors
    kmeans = KMeans(n_clusters=8, random_state=42)
    kmeans.fit(data)
    colors = kmeans.cluster_centers_

    # Button detection and analysis
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Analyze button consistency
    buttons = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h
        area = cv2.contourArea(contour)

        # Filter for button-like shapes
        if 0.5 < aspect_ratio < 4 and 500 < area < 10000:
            buttons.append({
                'location': (x, y, w, h),
                'aspect_ratio': aspect_ratio,
                'area': area
            })

    # Analyze size consistency
    button_sizes = [btn['area'] for btn in buttons]
    size_variance = np.var(button_sizes) if button_sizes else 0

    return {
        'dominant_colors': colors,
        'button_count': len(buttons),
        'size_consistency': 1 / (1 + size_variance)  # Higher = more consistent
    }
```

### **Analysis Prompt Template**
```
Evaluate consistency and standards adherence:

1. **Visual Consistency**: Are colors, fonts, and spacing used consistently?
2. **Interaction Patterns**: Do similar elements behave similarly throughout?
3. **Terminology**: Is language and labeling consistent across the interface?
4. **Layout Patterns**: Are similar functions positioned consistently?
5. **Platform Standards**: Does the interface follow platform-specific conventions?

Rate consistency: [Excellent/Good/Fair/Poor]
Identify inconsistencies and suggest standardization improvements.
```

---

## 5. Error Prevention

### **Definition**
Prevent errors from occurring in the first place through good design.

### **Evaluation Criteria**
- **Input Validation**: Real-time validation of form inputs
- **Confirmation Dialogs**: Confirmation for destructive actions
- **Constraints**: Preventing invalid selections or inputs
- **Clear Defaults**: Providing sensible default values
- **Guided Input**: Input formatting hints and examples

### **Computer Vision Detection Methods**
```python
# Example: Detect error prevention mechanisms
def detect_error_prevention(screenshot):
    import pytesseract

    # Look for validation messages and confirmation dialogs
    text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)

    prevention_indicators = {
        'confirmations': ['confirm', 'are you sure', 'delete', 'remove', 'permanent'],
        'validations': ['required', 'invalid', 'format', 'must', 'should'],
        'hints': ['example', 'format:', 'e.g.', 'hint', 'help']
    }

    found_indicators = {'confirmations': [], 'validations': [], 'hints': []}

    for i, word in enumerate(text_data['text']):
        for category, keywords in prevention_indicators.items():
            if any(keyword in word.lower() for keyword in keywords):
                x, y, w, h = (text_data['left'][i], text_data['top'][i],
                             text_data['width'][i], text_data['height'][i])
                found_indicators[category].append({
                    'text': word,
                    'location': (x, y, w, h)
                })

    # Detect form elements and their validation states
    # ... (implementation for detecting form fields and validation indicators)

    return found_indicators
```

### **Analysis Prompt Template**
```
Analyze error prevention mechanisms:

1. **Input Validation**: Are there real-time validation messages for form inputs?
2. **Confirmation Dialogs**: Are destructive actions protected by confirmation dialogs?
3. **Input Constraints**: Are invalid inputs prevented rather than just flagged?
4. **Default Values**: Are sensible defaults provided to prevent errors?
5. **Input Guidance**: Are there format hints and examples to guide users?

Rate error prevention: [Excellent/Good/Fair/Poor]
Identify areas where errors could be prevented proactively.
```

---

## 6. Recognition Rather Than Recall

### **Definition**
Make information and options visible rather than requiring users to remember them.

### **Evaluation Criteria**
- **Visible Options**: Actions and options are visible rather than hidden
- **Context Preservation**: Previous selections and states remain visible
- **Clear Labels**: Buttons and links clearly indicate their function
- **Visual Cues**: Icons and visual indicators aid recognition
- **Reduced Memory Load**: Minimize information users must remember

### **Computer Vision Detection Methods**
```python
# Example: Analyze visibility of options and information
def analyze_recognition_vs_recall(screenshot):
    # Detect hidden vs. visible elements
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    # Detect dropdown menus (hamburger menus, etc.)
    # Look for three horizontal lines pattern
    lines = cv2.HoughLinesP(gray, 1, np.pi/180, threshold=50,
                           minLineLength=20, maxLineGap=5)

    hamburger_menus = []
    if lines is not None:
        # Group horizontal lines that might form hamburger menu
        horizontal_lines = [line for line in lines
                           if abs(line[0][1] - line[0][3]) < 5]
        # ... (logic to detect hamburger menu patterns)

    # Detect visible navigation elements
    import pytesseract
    text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)

    # Count visible navigation terms
    nav_terms = ['home', 'about', 'contact', 'services', 'products', 'menu']
    visible_nav = sum(1 for word in text_data['text']
                     if word.lower() in nav_terms)

    return {
        'hamburger_menus': len(hamburger_menus),
        'visible_navigation': visible_nav,
        'total_text_elements': len([w for w in text_data['text'] if w.strip()])
    }
```

### **Analysis Prompt Template**
```
Evaluate recognition vs. recall design:

1. **Visible Options**: Are important actions and options clearly visible?
2. **Context Preservation**: Do users see their previous selections and current state?
3. **Clear Labeling**: Are buttons and links clearly labeled with their functions?
4. **Visual Cues**: Do icons and visual indicators support recognition?
5. **Memory Reduction**: Is the interface designed to minimize memory requirements?

Rate recognition support: [Excellent/Good/Fair/Poor]
Identify areas where hidden information should be made visible.
```

---

## 7. Flexibility and Efficiency of Use

### **Definition**
Provide accelerators and customization options for expert users while maintaining simplicity for novices.

### **Evaluation Criteria**
- **Keyboard Shortcuts**: Visible keyboard shortcuts for common actions
- **Customization Options**: Ability to customize interface elements
- **Multiple Paths**: Different ways to accomplish the same task
- **Quick Actions**: Shortcuts for frequent operations
- **Progressive Disclosure**: Advanced features available but not cluttering basic interface

### **Computer Vision Detection Methods**
```python
# Example: Detect efficiency features
def detect_efficiency_features(screenshot):
    import pytesseract

    # Look for keyboard shortcut indicators
    text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)

    # Common keyboard shortcut patterns
    shortcut_patterns = ['ctrl+', 'cmd+', 'alt+', 'shift+', 'f1', 'f2', 'esc']
    shortcuts_found = []

    for i, word in enumerate(text_data['text']):
        word_lower = word.lower()
        for pattern in shortcut_patterns:
            if pattern in word_lower:
                x, y, w, h = (text_data['left'][i], text_data['top'][i],
                             text_data['width'][i], text_data['height'][i])
                shortcuts_found.append({
                    'shortcut': word,
                    'location': (x, y, w, h)
                })

    # Detect customization elements (settings, preferences, etc.)
    customization_terms = ['settings', 'preferences', 'customize', 'options', 'configure']
    customization_found = []

    for i, word in enumerate(text_data['text']):
        if word.lower() in customization_terms:
            x, y, w, h = (text_data['left'][i], text_data['top'][i],
                         text_data['width'][i], text_data['height'][i])
            customization_found.append({
                'type': word,
                'location': (x, y, w, h)
            })

    return {
        'shortcuts': shortcuts_found,
        'customization_options': customization_found
    }
```

### **Analysis Prompt Template**
```
Assess flexibility and efficiency features:

1. **Keyboard Shortcuts**: Are keyboard shortcuts visible and available for common actions?
2. **Customization**: Can users customize the interface to their preferences?
3. **Multiple Paths**: Are there different ways to accomplish the same task?
4. **Quick Actions**: Are there shortcuts for frequently performed operations?
5. **Progressive Disclosure**: Are advanced features available without cluttering the basic interface?

Rate flexibility and efficiency: [Excellent/Good/Fair/Poor]
Suggest improvements for both novice and expert users.
```

---

## 8. Aesthetic and Minimalist Design

### **Definition**
Remove unnecessary elements and focus on essential information and functionality.

### **Evaluation Criteria**
- **Visual Hierarchy**: Clear importance ranking through size, color, and position
- **Whitespace Usage**: Appropriate use of whitespace to reduce clutter
- **Information Density**: Balanced information density - not too sparse or crowded
- **Color Harmony**: Cohesive color scheme that supports usability
- **Typography**: Clean, readable typography with appropriate hierarchy

### **Computer Vision Detection Methods**
```python
# Example: Analyze visual complexity and minimalism
def analyze_aesthetic_minimalism(screenshot):
    # Calculate visual complexity metrics
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    # Edge density (measure of visual complexity)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size

    # Color diversity
    from sklearn.cluster import KMeans
    data = screenshot.reshape((-1, 3))
    kmeans = KMeans(n_clusters=8, random_state=42)
    kmeans.fit(data)

    # Calculate color distribution entropy
    labels = kmeans.labels_
    color_counts = np.bincount(labels)
    color_entropy = -np.sum((color_counts / len(labels)) *
                           np.log2(color_counts / len(labels) + 1e-10))

    # Whitespace analysis
    # Convert to binary (assuming white background)
    _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    whitespace_ratio = np.sum(binary == 255) / binary.size

    # Text density
    import pytesseract
    text_data = pytesseract.image_to_string(screenshot)
    text_density = len(text_data.strip()) / (screenshot.shape[0] * screenshot.shape[1])

    return {
        'edge_density': edge_density,
        'color_entropy': color_entropy,
        'whitespace_ratio': whitespace_ratio,
        'text_density': text_density,
        'complexity_score': edge_density + color_entropy + (1 - whitespace_ratio)
    }
```

### **Analysis Prompt Template**
```
Evaluate aesthetic and minimalist design:

1. **Visual Hierarchy**: Is there a clear hierarchy of information importance?
2. **Whitespace**: Is whitespace used effectively to reduce visual clutter?
3. **Information Density**: Is the information density appropriate - not too sparse or crowded?
4. **Color Harmony**: Does the color scheme support usability and visual appeal?
5. **Typography**: Is the typography clean, readable, and well-hierarchized?

Rate aesthetic minimalism: [Excellent/Good/Fair/Poor]
Identify elements that could be simplified or removed.
```

---

## 9. Help Users Recognize, Diagnose, and Recover from Errors

### **Definition**
Error messages should be clear, helpful, and provide constructive solutions.

### **Evaluation Criteria**
- **Clear Error Messages**: Errors expressed in plain language
- **Specific Problem Identification**: Precise indication of what went wrong
- **Solution Suggestions**: Constructive suggestions for fixing the error
- **Visual Prominence**: Error messages are visually prominent and noticeable
- **Recovery Assistance**: Clear paths to recover from error states

### **Computer Vision Detection Methods**
```python
# Example: Detect and analyze error messages
def analyze_error_handling(screenshot):
    import pytesseract

    # Look for error-related colors (typically red)
    hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)

    # Define red color range
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])
    upper_red2 = np.array([180, 255, 255])

    # Create masks for red regions
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = mask1 + mask2

    # Find contours of red regions
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Extract text from red regions (likely error messages)
    error_regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > 50 and h > 10:  # Filter small regions
            roi = screenshot[y:y+h, x:x+w]
            text = pytesseract.image_to_string(roi).strip()
            if text:
                error_regions.append({
                    'location': (x, y, w, h),
                    'text': text
                })

    # Look for error-related keywords
    error_keywords = ['error', 'warning', 'failed', 'invalid', 'incorrect', 'required']
    text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)

    error_messages = []
    for i, word in enumerate(text_data['text']):
        if word.lower() in error_keywords:
            # Extract surrounding context
            context_start = max(0, i - 5)
            context_end = min(len(text_data['text']), i + 5)
            context = ' '.join(text_data['text'][context_start:context_end])

            error_messages.append({
                'keyword': word,
                'context': context,
                'location': (text_data['left'][i], text_data['top'][i],
                           text_data['width'][i], text_data['height'][i])
            })

    return {
        'red_regions': error_regions,
        'error_messages': error_messages
    }
```

### **Analysis Prompt Template**
```
Evaluate error handling and recovery:

1. **Message Clarity**: Are error messages written in plain, understandable language?
2. **Problem Identification**: Do errors clearly indicate what specific problem occurred?
3. **Solution Guidance**: Do error messages provide constructive suggestions for resolution?
4. **Visual Prominence**: Are error messages visually prominent and easy to notice?
5. **Recovery Path**: Is it clear how users can recover from error states?

Rate error handling: [Excellent/Good/Fair/Poor]
Identify improvements needed for error messages and recovery processes.
```

---

## 10. Help and Documentation

### **Definition**
Provide easily accessible, searchable, and task-focused help documentation.

### **Evaluation Criteria**
- **Accessibility**: Help is easy to find and access
- **Searchability**: Users can search for specific help topics
- **Task-Oriented**: Help focuses on user tasks rather than system features
- **Conciseness**: Information is concise and to the point
- **Visual Integration**: Help is integrated into the interface context

### **Computer Vision Detection Methods**
```python
# Example: Detect help and documentation elements
def detect_help_elements(screenshot):
    import pytesseract

    # Look for help-related terms and icons
    help_terms = ['help', 'support', 'faq', 'guide', 'tutorial', 'documentation',
                  'how to', 'tips', 'learn more', '?']

    text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)

    help_elements = []
    for i, word in enumerate(text_data['text']):
        word_lower = word.lower()
        for term in help_terms:
            if term in word_lower:
                x, y, w, h = (text_data['left'][i], text_data['top'][i],
                             text_data['width'][i], text_data['height'][i])
                help_elements.append({
                    'type': term,
                    'text': word,
                    'location': (x, y, w, h),
                    'confidence': text_data['conf'][i]
                })

    # Look for question mark icons (common help indicators)
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    # Template matching for question mark icons
    # (This would require a question mark template)
    # question_template = cv2.imread('question_mark_template.png', 0)
    # if question_template is not None:
    #     result = cv2.matchTemplate(gray, question_template, cv2.TM_CCOEFF_NORMED)
    #     locations = np.where(result >= 0.8)
    #     for pt in zip(*locations[::-1]):
    #         help_elements.append({
    #             'type': 'question_icon',
    #             'location': pt
    #         })

    return help_elements
```

### **Analysis Prompt Template**
```
Assess help and documentation:

1. **Accessibility**: Is help easy to find and access when needed?
2. **Search Functionality**: Can users search for specific help topics?
3. **Task Orientation**: Is help focused on user tasks rather than technical features?
4. **Conciseness**: Is help information concise and actionable?
5. **Context Integration**: Is help integrated contextually into the interface?

Rate help and documentation: [Excellent/Good/Fair/Poor]
Suggest improvements for help accessibility and usefulness.
```

---

## Comprehensive Analysis Framework

### **Master Analysis Prompt**
```
Conduct a comprehensive heuristic evaluation of this GUI screenshot:

**Screenshot Analysis Instructions:**
1. Examine the screenshot systematically for each of the 10 heuristics
2. Identify specific UI elements that exemplify good or poor adherence to each heuristic
3. Provide concrete examples with locations (e.g., "top navigation bar", "bottom-left button")
4. Rate each heuristic on a scale of 1-5 (1=Poor, 5=Excellent)
5. Prioritize issues by severity (Critical, High, Medium, Low)
6. Suggest specific, actionable improvements

**Output Format:**
```
# Heuristic Evaluation Report

## Overall Summary
- **Overall Usability Score**: X/50
- **Critical Issues**: [Count]
- **Key Strengths**: [List]
- **Priority Improvements**: [List]

## Detailed Analysis

### 1. Visibility of System Status - [Rating]/5
**Observations**: [Specific examples]
**Issues**: [Problems identified]
**Recommendations**: [Specific improvements]

[Continue for all 10 heuristics...]

## Prioritized Action Items
1. **Critical**: [Item] - Violates [Heuristic]
2. **High**: [Item] - Violates [Heuristic]
3. **Medium**: [Item] - Violates [Heuristic]

## Code Implementation Suggestions
```python
# Example improvements that could be implemented
```
```

### **Integration with Computer Vision Pipeline**
```python
# Complete analysis pipeline
def comprehensive_gui_analysis(screenshot_path):
    """
    Perform complete heuristic analysis of GUI screenshot
    """
    # Load screenshot
    screenshot = cv2.imread(screenshot_path)

    # Run all analysis functions
    results = {
        'visibility': analyze_system_status_visibility(screenshot),
        'real_world_match': analyze_icon_familiarity(screenshot),
        'user_control': detect_control_elements(screenshot),
        'consistency': analyze_consistency(screenshot),
        'error_prevention': detect_error_prevention(screenshot),
        'recognition': analyze_recognition_vs_recall(screenshot),
        'efficiency': detect_efficiency_features(screenshot),
        'minimalism': analyze_aesthetic_minimalism(screenshot),
        'error_handling': analyze_error_handling(screenshot),
        'help': detect_help_elements(screenshot)
    }

    # Generate comprehensive report
    report = generate_heuristic_report(results)

    return report, results

def generate_heuristic_report(analysis_results):
    """
    Generate human-readable report from analysis results
    """
    # Process results and create structured report
    # This would integrate with LLM for natural language generation
    pass
```

---

## Advanced Implementation Strategies

### **Multi-Modal Analysis Integration**
```python
# Combining computer vision with LLM analysis
class GUIHeuristicAnalyzer:
    def __init__(self, llm_client, cv_models):
        self.llm = llm_client
        self.cv_models = cv_models
        self.heuristics = self._load_heuristics()

    def analyze_screenshot(self, screenshot_path, context=None):
        """
        Complete analysis combining CV detection with LLM reasoning
        """
        # Stage 1: Computer Vision Analysis
        cv_results = self._run_cv_analysis(screenshot_path)

        # Stage 2: LLM Contextual Analysis
        llm_analysis = self._run_llm_analysis(screenshot_path, cv_results, context)

        # Stage 3: Synthesis and Scoring
        final_report = self._synthesize_results(cv_results, llm_analysis)

        return final_report

    def _run_cv_analysis(self, screenshot_path):
        """Run all computer vision detection methods"""
        screenshot = cv2.imread(screenshot_path)

        return {
            'elements_detected': self._detect_ui_elements(screenshot),
            'layout_analysis': self._analyze_layout(screenshot),
            'color_analysis': self._analyze_colors(screenshot),
            'text_analysis': self._analyze_text(screenshot),
            'interaction_elements': self._detect_interactive_elements(screenshot)
        }

    def _detect_ui_elements(self, screenshot):
        """Comprehensive UI element detection"""
        # Combine multiple detection approaches
        elements = []

        # 1. Contour-based detection
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            aspect_ratio = w / h if h > 0 else 0

            # Classify based on geometric properties
            element_type = self._classify_element_by_geometry(w, h, area, aspect_ratio)

            if element_type:
                elements.append({
                    'type': element_type,
                    'bbox': (x, y, w, h),
                    'area': area,
                    'aspect_ratio': aspect_ratio
                })

        # 2. Template matching for common UI elements
        templates = self._load_ui_templates()
        for template_name, template in templates.items():
            matches = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            locations = np.where(matches >= 0.8)

            for pt in zip(*locations[::-1]):
                elements.append({
                    'type': template_name,
                    'bbox': (pt[0], pt[1], template.shape[1], template.shape[0]),
                    'confidence': matches[pt[1], pt[0]]
                })

        return elements

    def _classify_element_by_geometry(self, w, h, area, aspect_ratio):
        """Classify UI elements based on geometric properties"""
        # Button detection
        if 50 < w < 300 and 20 < h < 80 and 1 < aspect_ratio < 6:
            return 'button'

        # Input field detection
        if 100 < w < 400 and 25 < h < 50 and aspect_ratio > 3:
            return 'input_field'

        # Image detection
        if area > 5000 and 0.5 < aspect_ratio < 2:
            return 'image'

        # Navigation bar detection
        if w > 200 and 30 < h < 100 and aspect_ratio > 4:
            return 'navigation_bar'

        return None
```

### **Context-Aware Heuristic Weighting**
```python
# Adaptive heuristic importance based on application type
HEURISTIC_WEIGHTS = {
    'e-commerce': {
        'visibility_of_system_status': 1.2,  # Critical for checkout processes
        'error_prevention': 1.3,  # Prevent costly transaction errors
        'user_control_freedom': 1.1,
        'consistency_standards': 1.0,
        'match_real_world': 1.0,
        'recognition_recall': 1.1,
        'flexibility_efficiency': 0.9,
        'aesthetic_minimalist': 1.1,
        'error_recovery': 1.2,
        'help_documentation': 0.8
    },
    'productivity': {
        'flexibility_efficiency': 1.4,  # Critical for power users
        'user_control_freedom': 1.3,
        'recognition_recall': 1.2,
        'consistency_standards': 1.2,
        'error_prevention': 1.1,
        'visibility_of_system_status': 1.0,
        'match_real_world': 1.0,
        'aesthetic_minimalist': 0.9,
        'error_recovery': 1.0,
        'help_documentation': 1.1
    },
    'mobile_app': {
        'aesthetic_minimalist': 1.3,  # Screen real estate is limited
        'recognition_recall': 1.3,  # Minimize cognitive load
        'user_control_freedom': 1.2,
        'match_real_world': 1.1,
        'consistency_standards': 1.1,
        'flexibility_efficiency': 0.8,  # Less relevant on mobile
        'visibility_of_system_status': 1.0,
        'error_prevention': 1.0,
        'error_recovery': 1.0,
        'help_documentation': 0.7
    }
}

def calculate_weighted_score(heuristic_scores, app_type='general'):
    """Calculate weighted usability score based on application context"""
    weights = HEURISTIC_WEIGHTS.get(app_type, {})

    weighted_scores = {}
    for heuristic, score in heuristic_scores.items():
        weight = weights.get(heuristic, 1.0)
        weighted_scores[heuristic] = score * weight

    return weighted_scores
```

### **Training Data Generation Framework**
```python
# Framework for generating training examples
class HeuristicTrainingDataGenerator:
    def __init__(self):
        self.good_examples = {}
        self.bad_examples = {}
        self.synthetic_generator = SyntheticGUIGenerator()

    def generate_training_set(self, heuristic, num_samples=1000):
        """Generate training examples for a specific heuristic"""
        training_data = []

        # Generate positive examples
        for _ in range(num_samples // 2):
            good_gui = self.synthetic_generator.create_good_example(heuristic)
            training_data.append({
                'image': good_gui,
                'heuristic': heuristic,
                'score': random.uniform(4.0, 5.0),
                'label': 'good',
                'explanation': self._generate_good_explanation(heuristic, good_gui)
            })

        # Generate negative examples
        for _ in range(num_samples // 2):
            bad_gui = self.synthetic_generator.create_bad_example(heuristic)
            training_data.append({
                'image': bad_gui,
                'heuristic': heuristic,
                'score': random.uniform(1.0, 2.5),
                'label': 'bad',
                'explanation': self._generate_bad_explanation(heuristic, bad_gui)
            })

        return training_data

    def create_few_shot_examples(self, heuristic):
        """Create few-shot learning examples for LLM"""
        return {
            'excellent_example': {
                'description': self._get_excellent_example(heuristic),
                'score': 5,
                'reasoning': self._get_excellent_reasoning(heuristic)
            },
            'poor_example': {
                'description': self._get_poor_example(heuristic),
                'score': 2,
                'reasoning': self._get_poor_reasoning(heuristic)
            }
        }
```

### **Real-World Integration Examples**

#### **Web Application Analysis**
```python
# Example: Analyzing a web application screenshot
def analyze_web_application(screenshot_path):
    """Specialized analysis for web applications"""

    # Load and preprocess
    screenshot = cv2.imread(screenshot_path)

    # Web-specific element detection
    web_elements = {
        'navigation': detect_navigation_elements(screenshot),
        'forms': detect_form_elements(screenshot),
        'buttons': detect_buttons(screenshot),
        'links': detect_links(screenshot),
        'content_areas': detect_content_areas(screenshot)
    }

    # Web-specific heuristic analysis
    analysis_prompts = {
        'navigation_consistency': """
        Analyze the navigation elements in this web interface:
        - Are navigation elements consistently positioned?
        - Is the main navigation easily identifiable?
        - Are there clear visual indicators for the current page?
        - Rate navigation consistency: [1-5]
        """,

        'form_usability': """
        Evaluate the form design in this interface:
        - Are form fields clearly labeled?
        - Is there clear validation feedback?
        - Are required fields indicated?
        - Is the form layout logical and scannable?
        - Rate form usability: [1-5]
        """,

        'responsive_design_indicators': """
        Assess responsive design elements:
        - Are there hamburger menus or other mobile-friendly elements?
        - Is the layout optimized for this screen size?
        - Are touch targets appropriately sized?
        - Rate responsive design: [1-5]
        """
    }

    return web_elements, analysis_prompts
```

#### **Mobile Application Analysis**
```python
# Example: Analyzing a mobile app screenshot
def analyze_mobile_application(screenshot_path):
    """Specialized analysis for mobile applications"""

    screenshot = cv2.imread(screenshot_path)

    # Mobile-specific considerations
    mobile_analysis = {
        'thumb_zone_analysis': analyze_thumb_reachability(screenshot),
        'touch_target_sizes': analyze_touch_targets(screenshot),
        'gesture_indicators': detect_gesture_hints(screenshot),
        'status_bar_integration': analyze_status_bar(screenshot)
    }

    mobile_prompts = {
        'thumb_reachability': """
        Analyze thumb reachability in this mobile interface:
        - Are primary actions within comfortable thumb reach?
        - Are frequently used controls in the thumb zone?
        - Is the interface optimized for one-handed use?
        - Rate thumb reachability: [1-5]
        """,

        'touch_targets': """
        Evaluate touch target sizing:
        - Are touch targets at least 44px × 44px?
        - Is there adequate spacing between interactive elements?
        - Are small targets avoided in favor of larger tap areas?
        - Rate touch target design: [1-5]
        """
    }

    return mobile_analysis, mobile_prompts

def analyze_thumb_reachability(screenshot):
    """Analyze how well the interface accommodates thumb interaction"""
    height, width = screenshot.shape[:2]

    # Define thumb-friendly zones (simplified model)
    easy_zone = (0, int(height * 0.5), width, height)  # Bottom half
    hard_zone = (0, 0, width, int(height * 0.25))  # Top quarter

    # Detect interactive elements
    interactive_elements = detect_interactive_elements(screenshot)

    easy_zone_elements = []
    hard_zone_elements = []

    for element in interactive_elements:
        x, y, w, h = element['bbox']
        center_y = y + h // 2

        if center_y >= easy_zone[1]:
            easy_zone_elements.append(element)
        elif center_y <= hard_zone[3]:
            hard_zone_elements.append(element)

    return {
        'easy_zone_count': len(easy_zone_elements),
        'hard_zone_count': len(hard_zone_elements),
        'thumb_friendliness_score': len(easy_zone_elements) / max(1, len(interactive_elements))
    }
```

### **Continuous Learning and Improvement**
```python
# Framework for improving analysis over time
class HeuristicAnalysisLearner:
    def __init__(self):
        self.feedback_database = FeedbackDatabase()
        self.model_updater = ModelUpdater()

    def collect_feedback(self, analysis_id, user_feedback):
        """Collect user feedback on analysis quality"""
        self.feedback_database.store_feedback({
            'analysis_id': analysis_id,
            'user_rating': user_feedback['rating'],
            'corrections': user_feedback['corrections'],
            'additional_issues': user_feedback['additional_issues'],
            'timestamp': datetime.now()
        })

    def update_analysis_models(self):
        """Update analysis based on collected feedback"""
        feedback_data = self.feedback_database.get_recent_feedback()

        # Identify common feedback patterns
        common_corrections = self._identify_patterns(feedback_data)

        # Update detection thresholds
        self._update_detection_parameters(common_corrections)

        # Update LLM prompts based on feedback
        self._refine_analysis_prompts(common_corrections)

    def _identify_patterns(self, feedback_data):
        """Identify common patterns in user feedback"""
        patterns = {}

        for feedback in feedback_data:
            for correction in feedback['corrections']:
                heuristic = correction['heuristic']
                issue_type = correction['issue_type']

                if heuristic not in patterns:
                    patterns[heuristic] = {}

                if issue_type not in patterns[heuristic]:
                    patterns[heuristic][issue_type] = 0

                patterns[heuristic][issue_type] += 1

        return patterns
```

### **Integration with Development Workflow**
```python
# Integration with CI/CD pipelines
class ContinuousUITesting:
    def __init__(self, gui_analyzer):
        self.analyzer = gui_analyzer
        self.baseline_scores = {}

    def setup_baseline(self, screenshots_dir):
        """Establish baseline usability scores"""
        for screenshot_file in os.listdir(screenshots_dir):
            if screenshot_file.endswith(('.png', '.jpg', '.jpeg')):
                analysis = self.analyzer.analyze_screenshot(
                    os.path.join(screenshots_dir, screenshot_file)
                )
                self.baseline_scores[screenshot_file] = analysis['overall_score']

    def regression_test(self, new_screenshots_dir, threshold=0.5):
        """Test for usability regression"""
        regressions = []

        for screenshot_file in os.listdir(new_screenshots_dir):
            if screenshot_file.endswith(('.png', '.jpg', '.jpeg')):
                new_analysis = self.analyzer.analyze_screenshot(
                    os.path.join(new_screenshots_dir, screenshot_file)
                )

                baseline_score = self.baseline_scores.get(screenshot_file, 0)
                score_diff = baseline_score - new_analysis['overall_score']

                if score_diff > threshold:
                    regressions.append({
                        'file': screenshot_file,
                        'baseline_score': baseline_score,
                        'current_score': new_analysis['overall_score'],
                        'regression': score_diff,
                        'critical_issues': new_analysis['critical_issues']
                    })

        return regressions

    def generate_ci_report(self, regressions):
        """Generate CI-friendly report"""
        if not regressions:
            return "✅ No usability regressions detected"

        report = "❌ Usability regressions detected:\n\n"
        for regression in regressions:
            report += f"**{regression['file']}**\n"
            report += f"- Score dropped from {regression['baseline_score']:.2f} to {regression['current_score']:.2f}\n"
            report += f"- Critical issues: {len(regression['critical_issues'])}\n\n"

        return report
```

### **API Integration Template**
```python
# REST API for GUI analysis service
from flask import Flask, request, jsonify
import base64
import io
from PIL import Image

app = Flask(__name__)
analyzer = GUIHeuristicAnalyzer(llm_client, cv_models)

@app.route('/analyze', methods=['POST'])
def analyze_gui():
    """API endpoint for GUI analysis"""
    try:
        # Handle base64 encoded image
        image_data = request.json['image']
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))

        # Optional context parameters
        app_type = request.json.get('app_type', 'general')
        focus_heuristics = request.json.get('focus_heuristics', None)

        # Perform analysis
        analysis_result = analyzer.analyze_screenshot(
            image,
            context={'app_type': app_type, 'focus': focus_heuristics}
        )

        return jsonify({
            'status': 'success',
            'analysis': analysis_result,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/batch_analyze', methods=['POST'])
def batch_analyze():
    """Batch analysis endpoint"""
    try:
        images = request.json['images']
        results = []

        for i, image_data in enumerate(images):
            try:
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))

                analysis = analyzer.analyze_screenshot(image)
                results.append({
                    'index': i,
                    'status': 'success',
                    'analysis': analysis
                })
            except Exception as e:
                results.append({
                    'index': i,
                    'status': 'error',
                    'error': str(e)
                })

        return jsonify({
            'status': 'success',
            'results': results
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

if __name__ == '__main__':
    app.run(debug=True)
```

---

This comprehensive instruction set provides your LLM coding assistant with:

### **Core Capabilities**
- **Detailed evaluation criteria** for each of Nielsen's 10 heuristics
- **Computer vision code examples** for automated UI element detection
- **Structured analysis prompts** for consistent evaluation
- **Context-aware weighting** for different application types

### **Advanced Features**
- **Multi-modal analysis** combining CV and LLM reasoning
- **Specialized analyzers** for web apps, mobile apps, and desktop applications
- **Training data generation** for continuous improvement
- **CI/CD integration** for automated usability testing

### **Production-Ready Components**
- **REST API template** for service deployment
- **Batch processing** capabilities for large-scale analysis
- **Feedback collection** and continuous learning framework
- **Regression testing** for detecting usability degradation

### **Key Benefits**
1. **Consistency**: Standardized evaluation criteria ensure reliable results
2. **Scalability**: Automated detection reduces manual analysis time
3. **Adaptability**: Context-aware weighting for different use cases
4. **Continuous Improvement**: Learning framework improves accuracy over time
5. **Integration-Ready**: APIs and tools for easy workflow integration

The system combines the reliability of established UX principles with the power of modern AI and computer vision to provide comprehensive, actionable GUI usability analysis.
