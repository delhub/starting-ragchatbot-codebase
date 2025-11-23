# Frontend Changes - Theme Toggle Feature

## Overview
Added a dark/light theme toggle feature to the Course Materials Assistant frontend. Users can now switch between dark and light themes with a single click, and their preference is saved in localStorage.

## Files Modified

### 1. `frontend/index.html`
**Changes:**
- Added a theme toggle button at the top of the body element (before the main container)
- Button includes both sun and moon SVG icons for visual feedback
- Positioned in the top-right corner using fixed positioning
- Includes proper ARIA label for accessibility

**Code Added:**
```html
<button class="theme-toggle" id="themeToggle" aria-label="Toggle theme">
    <!-- Sun icon for light theme -->
    <svg class="sun-icon">...</svg>
    <!-- Moon icon for dark theme -->
    <svg class="moon-icon">...</svg>
</button>
```

### 2. `frontend/style.css`
**Changes:**

#### Light Theme CSS Variables
- Added a complete set of CSS variables for light theme using `[data-theme="light"]` selector
- Light theme colors include:
  - Background: `#f8fafc` (light slate)
  - Surface: `#ffffff` (white)
  - Text primary: `#1e293b` (dark slate)
  - Text secondary: `#64748b` (medium slate)
  - Border: `#e2e8f0` (light gray)
  - Maintains the same primary blue (`#2563eb`) for consistency

#### Smooth Transitions
- Added global transition for smooth theme switching: `background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease`
- All elements now smoothly transition when theme changes

#### Theme Toggle Button Styles
- Circular button (44px × 44px) positioned fixed in top-right corner
- Hover effects: scale up (1.05) and slight icon rotation (20deg)
- Active state: scale down (0.95) for tactile feedback
- Focus state: visible focus ring for keyboard accessibility
- Icon visibility controlled by theme: shows moon in dark mode, sun in light mode
- Responsive: reduces to 40px × 40px on mobile devices

**Key CSS Sections:**
```css
/* Light Theme Variables */
[data-theme="light"] { ... }

/* Theme Toggle Button */
.theme-toggle { ... }

/* Icon visibility control */
[data-theme="light"] .theme-toggle .sun-icon { display: block; }
[data-theme="light"] .theme-toggle .moon-icon { display: none; }
```

### 3. `frontend/script.js`
**Changes:**

#### DOM Elements
- Added `themeToggle` to the global DOM elements

#### Event Listeners
- Added click event listener for theme toggle button
- Added keyboard event listener for Enter and Space keys (accessibility)

#### Theme Functions
Three new functions added:

1. **`initializeTheme()`**
   - Called on page load
   - Checks localStorage for saved theme preference
   - Defaults to dark theme if no preference saved
   - Applies the saved/default theme

2. **`toggleTheme()`**
   - Gets current theme from DOM
   - Toggles between 'dark' and 'light'
   - Applies new theme
   - Saves preference to localStorage

3. **`applyTheme(theme)`**
   - Sets or removes `data-theme` attribute on document element
   - Light theme: adds `data-theme="light"`
   - Dark theme: removes the attribute (default state)

## User Experience

### Visual Design
- **Dark Theme (Default):**
  - Dark blue/slate background (`#0f172a`)
  - Light text for high contrast
  - Moon icon visible in toggle button

- **Light Theme:**
  - Clean white/light slate background (`#f8fafc`)
  - Dark text for readability
  - Sun icon visible in toggle button

### Interaction
1. Click the circular button in the top-right corner to toggle themes
2. Keyboard users can tab to the button and press Enter or Space
3. Theme preference persists across page reloads via localStorage
4. Smooth 0.3s transitions provide polished visual feedback

### Accessibility Features
- ARIA label on toggle button: "Toggle theme"
- Keyboard navigable (Tab key)
- Keyboard activatable (Enter or Space keys)
- Clear focus ring indicator
- High contrast maintained in both themes
- Icons provide visual cues for current theme

## Technical Implementation

### Theme Switching Mechanism
- Uses CSS custom properties (variables) for all color values
- `data-theme` attribute on `<html>` element controls active theme
- No JavaScript-based style manipulation (pure CSS approach)
- Smooth CSS transitions handle animation

### Storage
- Uses `localStorage.setItem('theme', value)` to persist preference
- Retrieves with `localStorage.getItem('theme')`
- Survives page refreshes and browser restarts
- Scoped to the domain

### Browser Compatibility
- CSS custom properties: Modern browsers (IE11+ with fallbacks if needed)
- localStorage: All modern browsers
- SVG icons: All modern browsers
- CSS transitions: All modern browsers

## Testing Recommendations

1. **Visual Testing:**
   - Verify both themes render correctly
   - Check all UI components (sidebar, chat, buttons, inputs)
   - Test hover and focus states

2. **Functional Testing:**
   - Click toggle button multiple times
   - Refresh page and verify theme persists
   - Clear localStorage and verify default theme

3. **Accessibility Testing:**
   - Tab to button and verify focus indicator
   - Activate with keyboard (Enter/Space)
   - Test with screen reader (should announce "Toggle theme" button)

4. **Responsive Testing:**
   - Verify button position on mobile (1rem from edges)
   - Check button size on mobile (40px)
   - Ensure button doesn't overlap with sidebar on narrow screens

## Future Enhancements (Optional)

1. System theme detection: Use `prefers-color-scheme` media query to auto-detect user's OS theme
2. Additional themes: Could add more color schemes (blue, purple, etc.)
3. Smooth icon transitions: Add rotation or fade animations when switching icons
4. Accessibility: Add theme preference to a settings panel with descriptive labels
