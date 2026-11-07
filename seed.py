from app import app, create_record, get_db, init_db

TEAM = "Written by Team RA.1 as a demonstration record from general public knowledge."

SAMPLES = [
    {
        "title": "Five-Colour Temple Mural Panel",
        "creator": "Sample Mural Artist (demo)",
        "art_form": "Kerala mural painting",
        "region": "Central Kerala",
        "year": "",
        "cultural_context": "Kerala's temple mural tradition is known for a palette built around red, yellow, green, white and black, traditionally made from natural pigments. Murals usually show stories from epics and local legends.",
        "source": TEAM,
        "reuse_permission": "Non-commercial reuse with credit",
        "attribution_text": "Credit: Sample Mural Artist (demo), Kerala mural tradition.",
    },
    {
        "title": "Theyyam Face Painting Study",
        "creator": "Sample Theyyam Community (demo)",
        "art_form": "Theyyam",
        "region": "North Malabar",
        "year": "",
        "cultural_context": "Theyyam is a ritual performance tradition of North Malabar, performed at village shrines. It is a form of worship, so how it is photographed and shared matters to the communities who perform it.",
        "source": TEAM,
        "reuse_permission": "Ask the creator before reuse",
        "attribution_text": "Credit: Sample Theyyam Community (demo), North Malabar.",
    },
    {
        "title": "Kathakali Green Character Makeup",
        "creator": "Sample Kathakali Artist (demo)",
        "art_form": "Kathakali",
        "region": "Kerala",
        "year": "",
        "cultural_context": "Kathakali is a classical dance-drama of Kerala known for elaborate facial makeup, costumes and expressive hand gestures. Colours in the makeup indicate the type of character.",
        "source": TEAM,
        "reuse_permission": "Free to reuse with credit",
        "attribution_text": "Credit: Sample Kathakali Artist (demo), Kerala.",
    },
    {
        "title": "Handmade Metal Mirror",
        "creator": "Sample Aranmula Craftsperson (demo)",
        "art_form": "Aranmula kannadi (metal mirror)",
        "region": "Aranmula, Pathanamthitta",
        "year": "",
        "cultural_context": "The Aranmula kannadi is a handmade metal-alloy mirror from the Aranmula area. The exact method is traditionally described as a closely held craft skill passed down within families.",
        "source": TEAM,
        "reuse_permission": "Non-commercial reuse with credit",
        "attribution_text": "Credit: Sample Aranmula Craftsperson (demo), Aranmula.",
    },
    {
        "title": "Onam Pookalam Floral Carpet",
        "creator": "Sample Community Group (demo)",
        "art_form": "Pookalam (floral carpet)",
        "region": "Kerala",
        "year": "",
        "cultural_context": "A pookalam is a floral design made on the ground during Onam. Families and communities create it together, so the work is often collective rather than by one named artist.",
        "source": TEAM,
        "reuse_permission": "Free to reuse with credit",
        "attribution_text": "Credit: Sample Community Group (demo), Kerala.",
    },
    {
        "title": "Handloom Kasavu Border Sample",
        "creator": "Sample Weaver Cooperative (demo)",
        "art_form": "Kasavu handloom weaving",
        "region": "Balaramapuram, Thiruvananthapuram",
        "year": "",
        "cultural_context": "Kasavu cloth is an off-white handloom fabric with a golden border, worn in Kerala especially at festivals. Weaving communities in places like Balaramapuram keep the craft alive.",
        "source": TEAM,
        "reuse_permission": "Non-commercial reuse with credit",
        "attribution_text": "Credit: Sample Weaver Cooperative (demo), Balaramapuram.",
    },
    {
        "title": "Mohiniyattam Performance Still",
        "creator": "Sample Dancer (demo)",
        "art_form": "Mohiniyattam",
        "region": "Kerala",
        "year": "",
        "cultural_context": "Mohiniyattam is a classical dance form of Kerala, known for graceful swaying movements and gentle expression.",
        "source": TEAM,
        "reuse_permission": "Ask the creator before reuse",
        "attribution_text": "Credit: Sample Dancer (demo), Kerala.",
    },
    {
        "title": "Boat Song Recording",
        "creator": "Sample Rowing Group (demo)",
        "art_form": "Vanchippattu (boat songs)",
        "region": "Kuttanad, Alappuzha",
        "year": "",
        "cultural_context": "Vanchippattu are rhythmic boat songs sung by rowers in Kerala's backwaters, often linked to snake-boat races.",
        "source": TEAM,
        "reuse_permission": "Free to reuse with credit",
        "attribution_text": "Credit: Sample Rowing Group (demo), Kuttanad.",
    },
    {
        "title": "Tiger Dance Body Painting",
        "creator": "Sample Pulikali Troupe (demo)",
        "art_form": "Pulikali",
        "region": "Thrissur",
        "year": "",
        "cultural_context": "Pulikali is a folk performance of Thrissur during Onam in which performers paint their bodies as tigers and leopards and dance to drums.",
        "source": TEAM,
        "reuse_permission": "Non-commercial reuse with credit",
        "attribution_text": "Credit: Sample Pulikali Troupe (demo), Thrissur.",
    },
    {
        "title": "Kalaripayattu Practice Session",
        "creator": "Sample Kalari Gurukkal (demo)",
        "art_form": "Kalaripayattu",
        "region": "North Kerala",
        "year": "",
        "cultural_context": "Kalaripayattu is a traditional martial art of Kerala, taught in training halls called kalaris under a teacher called a gurukkal.",
        "source": TEAM,
        "reuse_permission": "Ask the creator before reuse",
        "attribution_text": "Credit: Sample Kalari Gurukkal (demo), Kerala.",
    },
    {
        "title": "Decorative Elephant Caparison",
        "creator": "Sample Craft Workshop (demo)",
        "art_form": "Nettipattam",
        "region": "Thrissur",
        "year": "",
        "cultural_context": "The nettipattam is a decorated ornament for elephants' foreheads used in temple festivals in Kerala, made by skilled craftspeople.",
        "source": TEAM,
        "reuse_permission": "Non-commercial reuse with credit",
        "attribution_text": "Credit: Sample Craft Workshop (demo), Thrissur.",
    },
    {
        "title": "Palm-Leaf Manuscript Page",
        "creator": "Sample Manuscript Scribe (demo)",
        "art_form": "Palm-leaf manuscripts",
        "region": "Kerala",
        "year": "",
        "cultural_context": "Before paper, texts in Kerala were commonly written by scratching letters into dried palm leaves with a stylus. Many manuscripts survive in libraries and families.",
        "source": TEAM,
        "reuse_permission": "Free to reuse with credit",
        "attribution_text": "Credit: Sample Manuscript Scribe (demo), Kerala.",
    },
]

with app.app_context():
    init_db()
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    if count:
        print(f"Database already has {count} records. Nothing added.")
    else:
        for sample in SAMPLES:
            create_record(db, sample, is_sample=True)
        print(f"Added {len(SAMPLES)} sample records.")