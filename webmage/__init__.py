from .spell import Spell

def WebMage(url, **kwargs):
    ghost = kwargs['ghost'] if 'ghost' in kwargs else False
    browser = kwargs['browser'] if 'browser' in kwargs else 'chrome'
    return Spell(url=url, ghost=ghost, browser=browser)


            

        
