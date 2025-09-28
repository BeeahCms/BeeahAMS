function applyTheme(theme) {
    const root = document.documentElement;
    let themeProps = {};

    switch (theme) {
        case 'light_blue':
            themeProps = {
                '--sidebar-bg': '#1E90FF',
                '--header-bg': '#FFFFFF',
                '--main-bg': '#F0F8FF',
                '--card-bg': '#FFFFFF',
                '--text-color': '#000000',
                '--header-text': '#1E90FF',
                '--primary-accent': '#1c75bc',
                '--card-shadow': '0 4px 15px rgba(30, 144, 255, 0.1)',
                '--card-border': '5px solid #1E90FF'
            };
            break;
        case 'forest_green':
            themeProps = {
                '--sidebar-bg': '#228B22',
                '--header-bg': '#FFFFFF',
                '--main-bg': '#F0FFF0',
                '--card-bg': '#FFFFFF',
                '--text-color': '#000000',
                '--header-text': '#228B22',
                '--primary-accent': '#1a681a',
                '--card-shadow': '0 4px 15px rgba(34, 139, 34, 0.1)',
                '--card-border': '5px solid #228B22'
            };
            break;
        case 'midnight_black':
            themeProps = {
                '--sidebar-bg': '#1a1a1a',
                '--header-bg': '#2b2b2b',
                '--main-bg': '#121212',
                '--card-bg': '#2b2b2b',
                '--text-color': '#FFFFFF',
                '--header-text': '#FFFFFF',
                '--primary-accent': '#007bff',
                '--light-text': '#a0a0a0',
                '--card-shadow': '0 5px 15px rgba(0, 123, 255, 0.1)',
                '--card-border': '5px solid #007bff'
            };
            break;
        case 'slate_grey':
             themeProps = {
                '--sidebar-bg': '#465461',
                '--header-bg': '#FFFFFF',
                '--main-bg': '#F1F1F1',
                '--card-bg': '#FFFFFF',
                '--text-color': '#333333',
                '--header-text': '#465461',
                '--primary-accent': '#5A6A78',
                '--card-shadow': '0 4px 12px rgba(70, 84, 97, 0.15)',
                '--card-border': '5px solid #465461'
            };
            break;
        case 'sunrise_orange':
            themeProps = {
                '--sidebar-bg': '#FF8C00',
                '--header-bg': '#FFFFFF',
                '--main-bg': '#FFF5E1',
                '--card-bg': '#FFFFFF',
                '--text-color': '#000000',
                '--header-text': '#E57D00',
                '--primary-accent': '#E57D00',
                '--card-shadow': '0 4px 15px rgba(255, 140, 0, 0.15)',
                '--card-border': '5px solid #FF8C00'
            };
            break;
        case 'royal_purple':
            themeProps = {
                '--sidebar-bg': '#6A0DAD',
                '--header-bg': '#FFFFFF',
                '--main-bg': '#F3E8FF',
                '--card-bg': '#FFFFFF',
                '--text-color': '#000000',
                '--header-text': '#6A0DAD',
                '--primary-accent': '#800080',
                '--card-shadow': '0 4px 15px rgba(106, 13, 173, 0.1)',
                '--card-border': '5px solid #6A0DAD'
            };
            break;
        case 'ocean_breeze':
            themeProps = {
                '--sidebar-bg': '#008B8B',
                '--header-bg': '#FFFFFF',
                '--main-bg': '#E0FFFF',
                '--card-bg': '#FFFFFF',
                '--text-color': '#000000',
                '--header-text': '#008B8B',
                '--primary-accent': '#20B2AA',
                '--card-shadow': '0 4px 15px rgba(0, 139, 139, 0.1)',
                '--card-border': '5px solid #008B8B'
            };
            break;
        case 'crimson_red':
             themeProps = {
                '--sidebar-bg': '#DC143C',
                '--header-bg': '#FFFFFF',
                '--main-bg': '#FFF0F5',
                '--card-bg': '#FFFFFF',
                '--text-color': '#000000',
                '--header-text': '#DC143C',
                '--primary-accent': '#c71236',
                '--card-shadow': '0 4px 15px rgba(220, 20, 60, 0.1)',
                '--card-border': '5px solid #DC143C'
            };
            break;
        case 'sandy_desert':
            themeProps = {
                '--sidebar-bg': '#D2B48C',
                '--header-bg': '#FFFFFF',
                '--main-bg': '#FAF0E6',
                '--card-bg': '#FFFFFF',
                '--text-color': '#5D4037',
                '--header-text': '#8B4513',
                '--primary-accent': '#8B4513',
                '--card-shadow': '0 4px 15px rgba(139, 69, 19, 0.1)',
                '--card-border': '5px solid #D2B48C'
            };
            break;
        default: // Default Dark Theme
            themeProps = {
                '--sidebar-bg': '#0a2540',
                '--header-bg': '#ffffff',
                '--main-bg': '#f4f7f6',
                '--card-bg': '#ffffff',
                '--text-color': '#333',
                '--header-text': '#0a2540',
                '--primary-accent': '#007bff',
                '--danger-accent': '#dc3545',
                '--light-text': '#b0c4de',
                '--card-shadow': '0 4px 12px rgba(0,0,0,0.05)',
                '--card-border': '5px solid #007bff'
            };
            break;
    }

    for (const key in themeProps) {
        root.style.setProperty(key, themeProps[key]);
    }
}

function setTheme(themeName) {
    localStorage.setItem('theme', themeName);
    applyTheme(themeName);
}

(function () {
    const savedTheme = localStorage.getItem('theme') || 'default';
    applyTheme(savedTheme);
})();