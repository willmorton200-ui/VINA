with open('d:/VINA/static/scanner.html', 'r', encoding='utf-8') as f:
    text = f.read()

target1 = "previewStep === 'profile' ||"
repl1 = "previewStep === 'profile' || previewStep === 'profile_bought' ||"
text = text.replace(target1, repl1, 1)

target2 = "} else if (pStep === 'profile') {\n                switchHubTab('profile');"
repl2 = """} else if (pStep === 'profile') {
                switchHubTab('profile');
            } else if (pStep === 'profile_bought') {
                switchHubTab('profile');
                setTimeout(function() {
                    var el = document.getElementById('profile-bought-wines-scroll');
                    if (el) el.scrollIntoView({ behavior: 'instant', block: 'center' });
                }, 300);"""
text = text.replace(target2, repl2, 1)

with open('d:/VINA/static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated scanner.html for profile_bought')
