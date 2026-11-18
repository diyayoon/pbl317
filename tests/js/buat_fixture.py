import json, re, sys
sys.path.insert(0, __import__("os").getcwd())
from app import buat_app
from app.config import TestingConfig
from app.extensions import db
from app.models import Category, Product

app = buat_app(TestingConfig)
data = [("Kursi Kayu Vintage","Furnitur","Kayu Mahoni",300000),("Meja Marmer Vintage","Furnitur","Marmer",900000),
        ("Lemari Hias","Furnitur","Kayu Jati",1500000),("Teko Porselen","Keramik","Porselen",250000),
        ("Piring Biru","Keramik","Porselen",120000),("Vas Naga","Keramik","Porselen",700000),
        ("Jam Dinding Kayu","Jam","Kayu",450000),("Jam Saku Perak","Jam","Perak",2200000),
        ("Kursi Rotan","Furnitur","Rotan",200000),("Kursi Goyang Kayu","Furnitur","Kayu Jati",800000)]
with app.app_context():
    db.create_all()
    cats = {}
    for n,k,m,h in data:
        c = cats.setdefault(k, Category(name=k, slug=k.lower(), icon="◆"))
        db.session.add(Product(category=c, name=n, slug=re.sub(r"\W+","-",n.lower()), description="", price=h, stock=3, era="1900–1949",
                               origin="Jawa", material=m, condition="Good", authenticity_status="Verified", image_alt=n))
    db.session.commit()
    c = app.test_client()
    fx = {"/katalog": c.get("/katalog").get_data(as_text=True)}
    for q in ["", "kursi", "kayu", "meja vintage", "tidakada", "KURSI", "kursi kayu"]:
        from urllib.parse import quote
        fx["/katalog/hasil?q="+quote(q)] = c.get("/katalog/hasil?q="+quote(q)).get_data(as_text=True)
    json.dump(fx, open("/tmp/albis_fixtures.json","w"))
print("fixture ok", len(fx))
