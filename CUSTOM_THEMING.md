# RetroClamp Custom Theming System

## 🎨 Overview

RetroClamp uses a **layered theming approach** combining the professional foundation of QDarkStyleSheet with custom RetroClamp-specific enhancements.

### **Architecture:**
```
QDarkStyleSheet (Base) + custom_overlay.qss (Enhancements) = Final Theme
```

## 📁 Theme Files

### **custom_overlay.qss**
Custom QSS file that sits on top of QDarkStyleSheet to provide:
- **RetroClamp branding colors** (Dracula theme palette)
- **Enhanced UI components** (buttons, inputs, navigation)
- **Consistent interaction feedback** (hover, focus, pressed states)
- **Professional polish** (tooltips, menus, dialogs)

### **Color Palette (Dracula-inspired)**
```qss
Primary: #bd93f9      /* Purple - main accent */
Secondary: #ff79c6    /* Pink - secondary accent */
Success: #50fa7b      /* Green - progress/success */
Warning: #ffb86c      /* Orange - warnings */
Error: #ff5555        /* Red - errors */
Info: #8be9fd         /* Cyan - information */

Background: #282a36   /* Main background */
Secondary BG: #44475a /* Secondary background */
Tertiary BG: #6272a4  /* Borders and separators */
Text: #f8f8f2         /* Primary text */
```

## 🎯 Enhanced Components

### **1. Checkbox & Radio Indicators**
- Restored proper visual indicators
- 16×16px size with 3px border radius
- Proper checked/unchecked states

### **2. Button States**
- **Hover**: Subtle background lightening
- **Pressed**: Purple accent with inverted text
- **Navigation**: Left border accent on hover/selection

### **3. Progress & Scrollbars**
- **Progress chunks**: Success green color
- **Scrollbar handles**: Consistent with theme palette
- **Hover states**: Visual feedback

### **4. Tabs**
- **Active tab**: Purple background with dark text
- **Hover**: Semi-transparent purple
- **Consistent**: Matches overall theme

### **5. Input Controls**
- **LineEdit**: Enhanced focus states
- **ComboBox**: Custom dropdown arrows
- **SpinBox**: Consistent styling
- **Borders**: Purple accent on focus

### **6. Navigation**
- **Sidebar buttons**: Left border accent
- **Hover effects**: Smooth background transitions
- **Selection states**: Clear visual hierarchy

## 🔧 Implementation

### **Automatic Loading**
The custom overlay is automatically loaded in `main.py`:

```python
# Load base QDarkStyleSheet
base_stylesheet = qdarkstyle.load_stylesheet_pyside6()

# Load custom overlay
with open("custom_overlay.qss", "r") as f:
    custom_overlay = f.read()

# Combine and apply
combined_stylesheet = base_stylesheet + "\n" + custom_overlay
app.setStyleSheet(combined_stylesheet)
```

### **Fallback Behavior**
- If `custom_overlay.qss` is missing → Uses QDarkStyleSheet only
- If QDarkStyleSheet is missing → Uses Qt default theme
- Graceful degradation ensures app always works

## 🎨 Customization

### **To Modify Colors:**
Edit the color values in `custom_overlay.qss`:

```qss
/* Change primary accent color */
QPushButton:pressed {
    background-color: #your-color-here;
}

/* Change hover effects */
QPushButton:hover {
    background-color: rgba(your, values, here, 0.08);
}
```

### **To Add New Components:**
Add new selectors to `custom_overlay.qss`:

```qss
/* New component styling */
QNewWidget {
    background: #282a36;
    border: 1px solid #6272a4;
    color: #f8f8f2;
}
```

### **Color Palette Variables**
For consistency, use these color values:

| Color | Hex | Usage |
|-------|-----|-------|
| `#bd93f9` | Purple | Primary accent, selections |
| `#44475a` | Dark Gray | Secondary backgrounds |
| `#6272a4` | Blue Gray | Borders, inactive elements |
| `#f8f8f2` | Off White | Primary text |
| `#282a36` | Dark | Main background |
| `#50fa7b` | Green | Success, progress |
| `#ff5555` | Red | Errors, warnings |

## 🚀 Benefits

### **Visual Improvements**
- ✅ **Professional appearance** matching commercial software
- ✅ **Consistent branding** throughout the application
- ✅ **Enhanced user feedback** for all interactions
- ✅ **Modern design language** with proper spacing and typography

### **Technical Benefits**
- ✅ **Maintainable**: Clear separation of base theme and customizations
- ✅ **Flexible**: Easy to modify colors and add new components
- ✅ **Reliable**: Built on top of mature QDarkStyleSheet foundation
- ✅ **Future-proof**: Updates to QDarkStyleSheet won't break customizations

### **User Experience**
- ✅ **Clear visual hierarchy** makes navigation intuitive
- ✅ **Consistent interactions** across all UI elements
- ✅ **Professional polish** enhances user confidence
- ✅ **Accessibility**: High contrast and clear indicators

## 📋 Maintenance

### **Updating Themes**
1. **QDarkStyleSheet updates**: Automatic via pip updates
2. **Custom overlay updates**: Edit `custom_overlay.qss` as needed
3. **Color scheme changes**: Update color values in overlay file
4. **New components**: Add selectors to overlay file

### **Testing**
After making changes to `custom_overlay.qss`:
1. Restart the application
2. Navigate through all tabs
3. Test all interactive elements
4. Verify color consistency

## 🎯 Result

The combination of QDarkStyleSheet + custom overlay creates a **professional, branded, and highly polished** user interface that:
- Looks like commercial software
- Maintains consistent visual language
- Provides excellent user experience
- Is easy to maintain and extend

**This theming system represents the best of both worlds: professional foundation with custom branding excellence!**
