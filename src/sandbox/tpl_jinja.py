
from docxtpl import DocxTemplate
from jinja2 import Environment
import jinja2
import docxtpl
import os
from pathlib import Path

print(jinja2.__version__)
print(jinja2.__file__)
print(docxtpl.__version__)
print(docxtpl.__file__)



# Eigener Filter
def multiply_by(value, by):
    return value * by

# Daten, die wir nacheinander einfügen wollen
preise = [10, 25, 50]

# Filter einmalig registrieren
jinja_env = Environment()
jinja_env.filters['multiply_by'] = multiply_by

# Schleife: Template jeweils frisch laden, Filter registrieren und rendern
for i, preis in enumerate(preise, start=1):
    # Template laden
    cwd = Path(__file__).parent
    print("Verzeichnis:", cwd)

    doc = DocxTemplate(cwd / "template.docx")
    assert doc is not None
    print(doc)
    print(f'{hasattr(doc, "jinja_env")= }')
    
    print("file existiert: ", os.path.exists(cwd / "template.docx"))
    # print("Platzhalter im Template:", doc.get_undeclared_template_variables())
    
    
    # exit(0)
    # assert doc.jinja_env is not None, "Jinja2-Environment konnte nicht erzeugt werden!"
    # doc.jinja_env.filters['multiply_by'] = multiply_by

    # Kontext für dieses Dokument
    context = {"price": preis}
   

    # Rendern
    doc.render(context, jinja_env=jinja_env )

    # Mit anderem Namen speichern
    doc.save(cwd / f"output_{i}.docx")

print("Fertig! Es wurden mehrere Dateien erzeugt.")