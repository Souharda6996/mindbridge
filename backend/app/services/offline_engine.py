"""Offline conversation engine v2 - no internet, no API key, four languages.

Why v2: v1 picked from small sentence pools and only avoided the *previous*
sentence, so the same validation, exercise offer and questions came back every
turn ("loop"), short answers like "yes"/"no" were ignored, and replies were
English-only.

How v2 works
  * Language  : every sentence exists in English, Hindi (Devanagari), Hinglish
                and Kannada; the reply uses the language the person wrote in.
  * Memory    : every sentence said in the session is remembered and never
                repeated while an unused alternative exists.
  * Stages    : each topic moves forward - validate -> explore -> deepen ->
                cope / CBT reframe -> practical tip -> summary & choice.
  * Intents   : "yes", "no", "I don't know", "what should I do?" and
                "I'm feeling better" get a fitting answer instead of a new question.
  * Restraint : each exercise is offered once (never again if declined); the
                counsellor offer appears at most every 4 turns; every few turns
                the reply simply holds space without asking anything.
"""
from __future__ import annotations

import random
import re

from .. import config
from . import smalltalk as st
from .i18n import LANGS, L


# --------------------------------------------------------------------------- topics
TOPIC_PATTERNS: dict[str, str] = {          # priority order: first match wins
    "panic": r"panic|heart (is )?racing|cant breathe|chest (is )?tight|anxiety attack|hyperventilat|saans nahi|घबराहट|साँस|ಉಸಿರು|ಆತಂಕ",
    "grief": r"died|passed away|funeral|grieving|death of|guzar ga|गुज़र|मौत|निधन|ತೀರಿಹೋದ|ಸಾವು",
    "overthinking": r"overthink|cant stop thinking|racing thoughts|keep thinking|what if|bahut sochta|bahut sochti|सोचता रहता|सोचती रहती|ज़्यादा सोच|ಯೋಚನೆ",
    "selfworth": r"not good enough|fail everything|failure|useless|compare myself|hate myself|worthless|bekaar|बेकार|नाकाम|ನಿಷ್ಪ್ರಯೋಜಕ",
    "exam": r"exam|tests?\b|marks|grades?\b|results?\b|study|studying|assignment|viva|semester|backlog|placement|interview|syllabus|padhai|पढ़ाई|परीक्षा|एग्जाम|रिजल्ट|ಪರೀಕ್ಷೆ|ಓದು|ಅಂಕ",
    "sleep": r"sleep|insomnia|awake all night|nightmare|neend|नींद|ನಿದ್ರೆ",
    "lonely": r"lonely|alone|isolated|left out|no friends|akela|akelapan|अकेला|अकेली|अकेलापन|ಒಂಟಿ",
    "relationship": r"breakup|broke up|girlfriend|boyfriend|relationship|partner|crush|ब्रेकअप|रिश्त|ಸಂಬಂಧ|ಪ್ರೀತಿ",
    "family": r"parents|mom\b|mommy|mother|dad\b|daddy|father|family|mummy|papa\b|ghar wale|माता|पिता|मम्मी|पापा|परिवार|घर वाले|ಅಪ್ಪ|ಅಮ್ಮ|ಕುಟುಂಬ|ಮನೆಯವರು",
    "work": r"jobs?\b|office|boss|manager|career|internship|naukri|नौकरी|ऑफिस|ಕೆಲಸ",
    "anger": r"angry|furious|unfair|gussa|गुस्सा|ಕೋಪ",
}

ABOUT = {   # "about <topic>" phrase, already in the right grammatical form per language
    None: L("about this", "इस बात के बारे में", "is baat ke baare mein", "ಇದರ ಬಗ್ಗೆ"),
    "panic": L("about these anxious moments", "घबराहट के बारे में", "ghabrahat ke baare mein", "ಆತಂಕದ ಬಗ್ಗೆ"),
    "grief": L("about this loss", "इस नुकसान के बारे में", "is loss ke baare mein", "ಈ ನಷ್ಟದ ಬಗ್ಗೆ"),
    "overthinking": L("about these thoughts", "इन विचारों के बारे में", "in thoughts ke baare mein", "ಈ ಯೋಚನೆಗಳ ಬಗ್ಗೆ"),
    "selfworth": L("about the way you see yourself", "खुद पर शक के बारे में", "khud pe shak ke baare mein", "ನಿಮ್ಮ ಮೇಲಿನ ಅನುಮಾನದ ಬಗ್ಗೆ"),
    "exam": L("about your exams", "परीक्षा के बारे में", "exams ke baare mein", "ಪರೀಕ್ಷೆಯ ಬಗ್ಗೆ"),
    "sleep": L("about your sleep", "नींद के बारे में", "neend ke baare mein", "ನಿದ್ರೆಯ ಬಗ್ಗೆ"),
    "lonely": L("about feeling alone", "अकेलेपन के बारे में", "akelepan ke baare mein", "ಒಂಟಿತನದ ಬಗ್ಗೆ"),
    "relationship": L("about this relationship", "इस रिश्ते के बारे में", "is relationship ke baare mein", "ಈ ಸಂಬಂಧದ ಬಗ್ಗೆ"),
    "family": L("about things at home", "घर की बातों के बारे में", "ghar ki baaton ke baare mein", "ಮನೆಯ ವಿಷಯಗಳ ಬಗ್ಗೆ"),
    "work": L("about work", "काम के बारे में", "kaam ke baare mein", "ಕೆಲಸದ ಬಗ್ಗೆ"),
    "anger": L("about what happened", "उस घटना के बारे में", "us baat ke baare mein", "ನಡೆದ ಘಟನೆಯ ಬಗ್ಗೆ"),
}

VALIDATE = {
    "exam": L("Exam pressure can make everything feel like it rides on one result, but you are much more than a mark sheet.",
              "परीक्षा का दबाव ऐसा महसूस करा सकता है जैसे सब कुछ एक नतीजे पर टिका हो, लेकिन आप एक मार्कशीट से कहीं ज़्यादा हैं।",
              "Exam ka pressure aisa feel kara sakta hai jaise sab kuch ek result par tika ho, par aap ek marksheet se kahin zyada ho.",
              "ಪರೀಕ್ಷೆಯ ಒತ್ತಡ ಎಲ್ಲವೂ ಒಂದೇ ಫಲಿತಾಂಶದ ಮೇಲೆ ನಿಂತಿದೆ ಅನ್ನಿಸುವಂತೆ ಮಾಡಬಹುದು, ಆದರೆ ನೀವು ಒಂದು ಅಂಕಪಟ್ಟಿಗಿಂತ ಎಷ್ಟೋ ಹೆಚ್ಚು."),
    "sleep": L("When sleep goes off track, everything else feels harder to manage.",
               "जब नींद बिगड़ जाती है, तो बाकी सब संभालना और मुश्किल लगने लगता है।",
               "Jab neend bigad jaati hai, toh baaki sab sambhalna aur mushkil lagta hai.",
               "ನಿದ್ರೆ ಸರಿಯಾಗಿ ಆಗದಿದ್ದಾಗ, ಉಳಿದೆಲ್ಲವನ್ನೂ ನಿಭಾಯಿಸುವುದು ಕಷ್ಟವಾಗುತ್ತದೆ."),
    "lonely": L("Feeling alone, even with people around, is one of the hardest feelings there is.",
                "लोगों के बीच रहकर भी अकेला महसूस करना सबसे कठिन एहसासों में से एक है।",
                "Logon ke beech rehkar bhi akela feel karna sabse mushkil feelings mein se ek hai.",
                "ಜನರ ನಡುವೆ ಇದ್ದರೂ ಒಂಟಿಯಾಗಿ ಅನ್ನಿಸುವುದು ತುಂಬಾ ಕಷ್ಟದ ಭಾವನೆ."),
    "relationship": L("When things go wrong with someone we care about, it can hurt almost physically.",
                      "जब किसी अपने के साथ चीज़ें बिगड़ती हैं, तो दर्द लगभग शारीरिक महसूस हो सकता है।",
                      "Jab kisi apne ke saath cheezein bigadti hain, toh dard almost physical lag sakta hai.",
                      "ನಾವು ಪ್ರೀತಿಸುವವರೊಂದಿಗೆ ಸಂಬಂಧ ಹಾಳಾದಾಗ, ಆ ನೋವು ದೇಹಕ್ಕೂ ತಾಗಿದಂತೆ ಅನ್ನಿಸಬಹುದು."),
    "family": L("Family situations get complicated, especially when you love them and still feel unheard.",
                "परिवार की बातें उलझ जाती हैं, खासकर जब आप उनसे प्यार करते हैं और फिर भी आपकी बात नहीं सुनी जाती।",
                "Family ki baatein uljh jaati hain, especially jab aap unse pyaar karte ho aur phir bhi aapki baat nahi suni jaati.",
                "ಮನೆಯವರನ್ನು ಪ್ರೀತಿಸಿದರೂ ಅವರು ನಮ್ಮ ಮಾತು ಕೇಳದಿದ್ದಾಗ, ಕುಟುಂಬದ ವಿಷಯಗಳು ಜಟಿಲವಾಗುತ್ತವೆ."),
    "panic": L("What you're describing sounds like your body's alarm system firing. It's frightening, but it does pass.",
               "आप जो बता रहे हैं वह शरीर के अलार्म सिस्टम जैसा लगता है। यह डरावना होता है, पर यह गुज़र जाता है।",
               "Aap jo bata rahe ho woh body ke alarm system jaisa lagta hai. Darawna hota hai, par yeh guzar jaata hai.",
               "ನೀವು ಹೇಳುತ್ತಿರುವುದು ದೇಹದ ಎಚ್ಚರಿಕೆ ವ್ಯವಸ್ಥೆ ಕೆಲಸ ಮಾಡುತ್ತಿರುವಂತೆ ಕಾಣುತ್ತದೆ. ಇದು ಭಯ ಹುಟ್ಟಿಸುತ್ತದೆ, ಆದರೆ ಇದು ಕಳೆದುಹೋಗುತ್ತದೆ."),
    "overthinking": L("Racing thoughts can make small worries feel enormous.",
                      "लगातार चलते विचार छोटी चिंताओं को भी बहुत बड़ा बना देते हैं।",
                      "Lagataar chalte thoughts chhoti chintaon ko bhi bahut bada bana dete hain.",
                      "ನಿಲ್ಲದ ಯೋಚನೆಗಳು ಸಣ್ಣ ಚಿಂತೆಗಳನ್ನೂ ತುಂಬಾ ದೊಡ್ಡದಾಗಿ ತೋರಿಸುತ್ತವೆ."),
    "selfworth": L("Comparing ourselves to others is something almost every student struggles with, even the ones who look fine.",
                   "खुद की दूसरों से तुलना करना लगभग हर छात्र करता है, वे भी जो बाहर से ठीक दिखते हैं।",
                   "Khud ko doosron se compare karna almost har student karta hai, woh bhi jo bahar se theek dikhte hain.",
                   "ಇತರರೊಂದಿಗೆ ನಮ್ಮನ್ನು ಹೋಲಿಸಿಕೊಳ್ಳುವುದು ಬಹುತೇಕ ಎಲ್ಲ ವಿದ್ಯಾರ್ಥಿಗಳೂ ಎದುರಿಸುವ ಸಮಸ್ಯೆ, ಹೊರಗೆ ಚೆನ್ನಾಗಿ ಕಾಣುವವರೂ ಸಹ."),
    "grief": L("I'm so sorry. Grief doesn't follow any timetable.",
               "मुझे बहुत दुख है। शोक का कोई तय समय नहीं होता।",
               "Mujhe bahut dukh hai. Grief ka koi fixed time nahi hota.",
               "ನನಗೆ ತುಂಬಾ ಬೇಸರವಾಗಿದೆ. ದುಃಖಕ್ಕೆ ಯಾವುದೇ ವೇಳಾಪಟ್ಟಿ ಇರುವುದಿಲ್ಲ."),
    "work": L("Work pressure has a way of following you home.",
              "काम का दबाव अक्सर घर तक पीछा करता है।",
              "Kaam ka pressure aksar ghar tak peecha karta hai.",
              "ಕೆಲಸದ ಒತ್ತಡ ಆಗಾಗ ಮನೆಯವರೆಗೂ ಹಿಂಬಾಲಿಸುತ್ತದೆ."),
    "anger": L("Anger often shows up when something important to us has been crossed.",
               "गुस्सा अक्सर तब आता है जब हमारे लिए कोई ज़रूरी बात टूटती है।",
               "Gussa aksar tab aata hai jab hamare liye koi important cheez cross hoti hai.",
               "ನಮಗೆ ಮುಖ್ಯವಾದ ಯಾವುದಾದರೂ ವಿಷಯಕ್ಕೆ ಧಕ್ಕೆಯಾದಾಗ ಕೋಪ ಬರುತ್ತದೆ."),
}

TIPS = {
    None: L("Something small that can help right now: a glass of water, a few slow breaths, and five minutes away from the screen.",
            "अभी के लिए एक छोटी मदद: एक गिलास पानी, कुछ धीमी साँसें, और पाँच मिनट के लिए स्क्रीन से दूरी।",
            "Abhi ke liye ek chhoti help: ek glass paani, kuch dheemi saansein, aur paanch minute screen se door.",
            "ಈಗಲೇ ಸಹಾಯ ಮಾಡಬಹುದಾದ ಸಣ್ಣ ವಿಷಯ: ಒಂದು ಲೋಟ ನೀರು, ಕೆಲವು ನಿಧಾನ ಉಸಿರುಗಳು, ಮತ್ತು ಐದು ನಿಮಿಷ ಪರದೆಯಿಂದ ದೂರ."),
    "exam": L("One thing that often helps: split tomorrow into three 40-minute study blocks with short breaks, and start with the easiest topic to build momentum.",
              "एक तरीका जो अक्सर मदद करता है: कल के दिन को 40-40 मिनट के तीन हिस्सों में बाँटिए, बीच में छोटे ब्रेक लीजिए, और सबसे आसान टॉपिक से शुरुआत कीजिए।",
              "Ek cheez jo aksar help karti hai: kal ko 40-40 minute ke teen study blocks mein baant lo, beech mein chhote breaks, aur sabse easy topic se start karo.",
              "ಸಾಮಾನ್ಯವಾಗಿ ಸಹಾಯ ಮಾಡುವುದು: ನಾಳೆಯನ್ನು 40 ನಿಮಿಷಗಳ ಮೂರು ಓದಿನ ಭಾಗಗಳಾಗಿ ವಿಂಗಡಿಸಿ, ನಡುವೆ ಸಣ್ಣ ವಿರಾಮ ತೆಗೆದುಕೊಳ್ಳಿ, ಮತ್ತು ಸುಲಭದ ವಿಷಯದಿಂದ ಶುರುಮಾಡಿ."),
    "sleep": L("A small change that helps many people: put the phone away 30 minutes before bed and write tomorrow's worries on paper so your mind can let go.",
               "कई लोगों को इससे मदद मिलती है: सोने से 30 मिनट पहले फ़ोन दूर रख दीजिए और कल की चिंताएँ कागज़ पर लिख दीजिए ताकि मन हल्का हो सके।",
               "Bahut logon ko isse help milti hai: sone se 30 minute pehle phone door rakh do aur kal ki tensions kaagaz pe likh do taaki dimaag halka ho.",
               "ಅನೇಕರಿಗೆ ಸಹಾಯ ಮಾಡುವ ಸಣ್ಣ ಬದಲಾವಣೆ: ಮಲಗುವ 30 ನಿಮಿಷ ಮೊದಲು ಫೋನ್ ದೂರವಿಡಿ ಮತ್ತು ನಾಳೆಯ ಚಿಂತೆಗಳನ್ನು ಕಾಗದದ ಮೇಲೆ ಬರೆಯಿರಿ."),
    "lonely": L("Connection often starts small: one message to someone you used to be close to, or sitting with classmates at lunch even without talking much.",
                "जुड़ाव अक्सर छोटे कदम से शुरू होता है: किसी पुराने करीबी को एक मैसेज, या लंच पर साथियों के साथ बैठ जाना।",
                "Connection aksar chhote step se shuru hota hai: kisi purane close dost ko ek message, ya lunch pe classmates ke saath baith jaana.",
                "ಸಂಪರ್ಕ ಸಣ್ಣ ಹೆಜ್ಜೆಯಿಂದ ಶುರುವಾಗುತ್ತದೆ: ಹಿಂದೆ ಹತ್ತಿರವಿದ್ದ ಯಾರಿಗಾದರೂ ಒಂದು ಸಂದೇಶ, ಅಥವಾ ಊಟದ ಸಮಯದಲ್ಲಿ ಸಹಪಾಠಿಗಳ ಜೊತೆ ಕುಳಿತುಕೊಳ್ಳುವುದು."),
    "relationship": L("It can help to give the feelings somewhere to go: write an unsent letter saying everything you wish you could say.",
                      "भावनाओं को बाहर निकलने का रास्ता देना मदद करता है: एक चिट्ठी लिखिए जिसमें वह सब हो जो आप कहना चाहते हैं, उसे भेजना ज़रूरी नहीं।",
                      "Feelings ko bahar nikalne ka raasta dena help karta hai: ek letter likho jismein woh sab ho jo aap kehna chahte ho, bhejna zaroori nahi.",
                      "ಭಾವನೆಗಳಿಗೆ ದಾರಿ ಕೊಡುವುದು ಸಹಾಯ ಮಾಡುತ್ತದೆ: ನೀವು ಹೇಳಬೇಕೆಂದಿರುವುದೆಲ್ಲವನ್ನೂ ಒಂದು ಪತ್ರದಲ್ಲಿ ಬರೆಯಿರಿ, ಅದನ್ನು ಕಳುಹಿಸುವ ಅಗತ್ಯವಿಲ್ಲ."),
    "family": L("Sometimes it helps to choose one calm moment and share just one thing you need from them, starting with 'I feel' instead of 'you always'.",
                "कभी-कभी किसी शांत पल में उनसे सिर्फ़ एक बात कहना मदद करता है, 'तुम हमेशा' की जगह 'मुझे ऐसा लगता है' से शुरू करके।",
                "Kabhi kabhi kisi shaant moment mein unse sirf ek baat kehna help karta hai, 'tum hamesha' ki jagah 'mujhe aisa lagta hai' se shuru karke.",
                "ಶಾಂತ ಸಮಯದಲ್ಲಿ, 'ನೀವು ಯಾವಾಗಲೂ' ಎನ್ನುವ ಬದಲು 'ನನಗೆ ಹೀಗೆ ಅನ್ನಿಸುತ್ತದೆ' ಎಂದು ಶುರುಮಾಡಿ, ನಿಮಗೆ ಬೇಕಾದ ಒಂದೇ ವಿಷಯ ಹೇಳುವುದು ಸಹಾಯ ಮಾಡಬಹುದು."),
    "panic": L("When it starts, try breathing out for longer than you breathe in, and name five things you can see. It tells your body you are safe.",
               "जब घबराहट शुरू हो, तो साँस अंदर लेने से ज़्यादा देर तक बाहर छोड़िए और आसपास की पाँच चीज़ों के नाम लीजिए। इससे शरीर को संकेत मिलता है कि आप सुरक्षित हैं।",
               "Jab ghabrahat shuru ho, toh saans andar lene se zyada der tak bahar chhodo aur aas-paas ki paanch cheezon ke naam lo. Isse body ko signal milta hai ki aap safe ho.",
               "ಆತಂಕ ಶುರುವಾದಾಗ, ಉಸಿರು ಒಳಗೆ ತೆಗೆದುಕೊಳ್ಳುವುದಕ್ಕಿಂತ ಹೆಚ್ಚು ಸಮಯ ಹೊರಗೆ ಬಿಡಿ ಮತ್ತು ಕಾಣುವ ಐದು ವಸ್ತುಗಳ ಹೆಸರು ಹೇಳಿ. ನೀವು ಸುರಕ್ಷಿತರು ಎಂದು ದೇಹಕ್ಕೆ ಅರಿವಾಗುತ್ತದೆ."),
    "overthinking": L("Try a 15-minute 'worry window' each evening: write the worries down then, and when they show up at other times, remind yourself they have a slot.",
                      "हर शाम 15 मिनट का 'चिंता समय' तय कीजिए: तब चिंताएँ लिखिए, और बाकी समय वे आएँ तो खुद को याद दिलाइए कि उनका समय तय है।",
                      "Har shaam 15 minute ka 'worry time' fix karo: tab saari tensions likho, aur baaki time aayein toh khud ko yaad dilao ki unka time fix hai.",
                      "ಪ್ರತಿ ಸಂಜೆ 15 ನಿಮಿಷದ 'ಚಿಂತೆಯ ಸಮಯ' ಇಡಿ: ಆಗ ಚಿಂತೆಗಳನ್ನು ಬರೆಯಿರಿ, ಬೇರೆ ಸಮಯದಲ್ಲಿ ಬಂದರೆ ಅವುಗಳಿಗೆ ಸಮಯ ಮೀಸಲಿದೆ ಎಂದು ನೆನಪಿಸಿಕೊಳ್ಳಿ."),
    "selfworth": L("Tonight, try writing down three things you handled today, however small. The mind notices failures automatically; strengths need a little help.",
                   "आज रात तीन ऐसी चीज़ें लिखिए जो आपने आज संभालीं, चाहे कितनी भी छोटी हों। मन गलतियाँ खुद गिन लेता है, अच्छाइयों को थोड़ी मदद चाहिए।",
                   "Aaj raat teen aisi cheezein likho jo aapne aaj sambhali, chahe kitni bhi chhoti hon. Dimaag galtiyan khud gin leta hai, achchaiyon ko thodi help chahiye.",
                   "ಇಂದು ರಾತ್ರಿ, ಇವತ್ತು ನೀವು ನಿಭಾಯಿಸಿದ ಮೂರು ವಿಷಯಗಳನ್ನು ಬರೆಯಿರಿ, ಎಷ್ಟೇ ಚಿಕ್ಕದಾಗಿರಲಿ. ಮನಸ್ಸು ತಪ್ಪುಗಳನ್ನು ತಾನೇ ಗಮನಿಸುತ್ತದೆ; ಒಳ್ಳೆಯದನ್ನು ಗಮನಿಸಲು ಸ್ವಲ್ಪ ಸಹಾಯ ಬೇಕು."),
    "grief": L("Some people find comfort in a small ritual: lighting a lamp, looking at a photo, or writing to the person about your day.",
               "कुछ लोगों को एक छोटी सी रस्म से सुकून मिलता है: दीया जलाना, कोई तस्वीर देखना, या उस व्यक्ति को अपने दिन के बारे में लिखना।",
               "Kuch logon ko ek chhoti si rasm se sukoon milta hai: diya jalana, koi photo dekhna, ya us insaan ko apne din ke baare mein likhna.",
               "ಕೆಲವರಿಗೆ ಸಣ್ಣ ಆಚರಣೆಯಿಂದ ಸಮಾಧಾನ ಸಿಗುತ್ತದೆ: ದೀಪ ಹಚ್ಚುವುದು, ಫೋಟೋ ನೋಡುವುದು, ಅಥವಾ ಆ ವ್ಯಕ್ತಿಗೆ ನಿಮ್ಮ ದಿನದ ಬಗ್ಗೆ ಬರೆಯುವುದು."),
    "work": L("It can help to draw a clear end to the workday: a short walk, a change of clothes, or writing tomorrow's top three tasks and closing the laptop.",
              "काम के दिन का साफ़ अंत करना मदद करता है: थोड़ी देर टहलना, कपड़े बदलना, या कल के तीन ज़रूरी काम लिखकर लैपटॉप बंद कर देना।",
              "Kaam ke din ka clear end karna help karta hai: thodi der walk, kapde badalna, ya kal ke top teen kaam likh kar laptop band kar dena.",
              "ಕೆಲಸದ ದಿನಕ್ಕೆ ಸ್ಪಷ್ಟ ಅಂತ್ಯ ಕೊಡುವುದು ಸಹಾಯ ಮಾಡುತ್ತದೆ: ಸ್ವಲ್ಪ ನಡಿಗೆ, ಬಟ್ಟೆ ಬದಲಾಯಿಸುವುದು, ಅಥವಾ ನಾಳೆಯ ಮೂರು ಮುಖ್ಯ ಕೆಲಸಗಳನ್ನು ಬರೆದು ಲ್ಯಾಪ್‌ಟಾಪ್ ಮುಚ್ಚುವುದು."),
    "anger": L("Before responding to whoever upset you, give it twenty minutes and some movement. Anger settles faster in the body than in the mind.",
               "जिससे आप नाराज़ हैं उसे जवाब देने से पहले बीस मिनट रुकिए और थोड़ा चल-फिर लीजिए। गुस्सा मन से पहले शरीर में शांत होता है।",
               "Jisse aap naraz ho usse jawab dene se pehle bees minute ruko aur thoda walk kar lo. Gussa dimaag se pehle body mein shaant hota hai.",
               "ನಿಮಗೆ ಬೇಸರ ಮಾಡಿದವರಿಗೆ ಉತ್ತರಿಸುವ ಮೊದಲು ಇಪ್ಪತ್ತು ನಿಮಿಷ ಕಾಯಿರಿ ಮತ್ತು ಸ್ವಲ್ಪ ಓಡಾಡಿ. ಕೋಪ ಮನಸ್ಸಿಗಿಂತ ಮೊದಲು ದೇಹದಲ್ಲಿ ಶಮನವಾಗುತ್ತದೆ."),
}

# --------------------------------------------------------------------------- pools
REFLECT = {
    "sadness": L(["That sounds really heavy to carry.", "I can hear how low things feel right now.",
                  "It makes sense that you'd feel drained after all this.", "That sounds genuinely painful."],
                 ["यह सच में बहुत भारी लग रहा है।", "आपकी बातों में कितनी उदासी है, यह साफ़ महसूस हो रहा है।",
                  "इतना सब झेलने के बाद थकान महसूस होना स्वाभाविक है।", "यह सच में दर्द भरा लगता है।"],
                 ["Yeh sach mein bahut bhaari lag raha hai.", "Aapki baaton mein kitni udaasi hai, saaf feel ho raha hai.",
                  "Itna sab jhelne ke baad thakaan feel hona natural hai.", "Yeh sach mein dard bhara lagta hai."],
                 ["ಇದು ನಿಜವಾಗಿಯೂ ತುಂಬಾ ಭಾರವಾಗಿದೆ ಅನ್ನಿಸುತ್ತದೆ.", "ನಿಮ್ಮ ಮಾತಿನಲ್ಲಿ ಎಷ್ಟು ನೋವಿದೆ ಎಂದು ಅರ್ಥವಾಗುತ್ತಿದೆ.",
                  "ಇಷ್ಟೆಲ್ಲಾ ಆದ ಮೇಲೆ ದಣಿವಾಗುವುದು ಸಹಜ."]),
    "fear": L(["That sounds stressful, like your mind won't let you rest.", "Worry like that can be exhausting to live with.",
               "It sounds like there's a lot of pressure sitting on you."],
              ["यह काफ़ी तनाव भरा लगता है, जैसे मन आराम ही नहीं करने दे रहा।", "ऐसी चिंता के साथ जीना थका देता है।",
               "लगता है आप पर काफ़ी दबाव है।"],
              ["Yeh kaafi stressful lagta hai, jaise dimaag aaram hi nahi karne de raha.", "Aisi tension ke saath rehna thaka deta hai.",
               "Lagta hai aap par kaafi pressure hai."],
              ["ಇದು ತುಂಬಾ ಒತ್ತಡದಂತೆ ಕಾಣುತ್ತದೆ, ಮನಸ್ಸಿಗೆ ವಿಶ್ರಾಂತಿಯೇ ಇಲ್ಲದಂತೆ.", "ಇಂತಹ ಚಿಂತೆಯೊಂದಿಗೆ ಬದುಕುವುದು ದಣಿಸುತ್ತದೆ.",
               "ನಿಮ್ಮ ಮೇಲೆ ತುಂಬಾ ಒತ್ತಡ ಇದ್ದಂತೆ ಕಾಣುತ್ತದೆ."]),
    "anger": L(["It sounds like something really got under your skin, and that's understandable.",
                "That would frustrate most people in your place.", "Your frustration makes sense; something feels unfair here."],
               ["लगता है किसी बात ने आपको सच में चुभा है, और यह समझ में आता है।", "आपकी जगह कोई भी होता तो उसे भी गुस्सा आता।",
                "आपकी नाराज़गी जायज़ लगती है, यहाँ कुछ गलत हुआ है।"],
               ["Lagta hai kisi baat ne aapko sach mein chubha hai, aur yeh samajh aata hai.",
                "Aapki jagah koi bhi hota toh usse bhi gussa aata.", "Aapki narazgi jaayaz lagti hai, yahan kuch galat hua hai."],
               ["ಯಾವುದೋ ವಿಷಯ ನಿಮಗೆ ನಿಜವಾಗಿಯೂ ನೋವು ಕೊಟ್ಟಿದೆ, ಅದು ಅರ್ಥವಾಗುತ್ತದೆ.", "ನಿಮ್ಮ ಸ್ಥಾನದಲ್ಲಿ ಯಾರಿದ್ದರೂ ಕೋಪ ಬರುತ್ತಿತ್ತು.",
                "ನಿಮ್ಮ ಅಸಮಾಧಾನ ಸರಿಯಾಗಿದೆ, ಇಲ್ಲಿ ಏನೋ ಅನ್ಯಾಯವಾಗಿದೆ."]),
    "joy": L(["That's genuinely good to hear.", "I love hearing that.", "It sounds like something went right today."],
             ["यह सुनकर सच में अच्छा लगा।", "कितनी अच्छी बात है!", "लगता है आज कुछ अच्छा हुआ है।"],
             ["Yeh sunkar sach mein accha laga.", "Kitni acchi baat hai!", "Lagta hai aaj kuch accha hua hai."],
             ["ಇದನ್ನು ಕೇಳಿ ನಿಜವಾಗಿಯೂ ಖುಷಿಯಾಯಿತು.", "ಎಷ್ಟು ಒಳ್ಳೆಯ ವಿಷಯ!", "ಇಂದು ಏನೋ ಒಳ್ಳೆಯದು ನಡೆದಂತೆ ಕಾಣುತ್ತದೆ."]),
    "surprise": L(["That sounds like a lot to take in.", "That must have caught you off guard."],
                  ["यह एक साथ समझने के लिए काफ़ी कुछ है।", "यह तो अचानक हुआ होगा।"],
                  ["Yeh ek saath samajhne ke liye kaafi kuch hai.", "Yeh toh achanak hua hoga."],
                  ["ಇದು ಒಮ್ಮೆಗೇ ಅರಗಿಸಿಕೊಳ್ಳಲು ತುಂಬಾ ಇದೆ.", "ಇದು ಅನಿರೀಕ್ಷಿತವಾಗಿರಬೇಕು."]),
    "neutral": L(["Thank you for telling me.", "I'm glad you shared that with me.", "Okay, I'm with you.", "I hear you."],
                 ["मुझे बताने के लिए धन्यवाद।", "अच्छा किया जो आपने यह बताया।", "ठीक है, मैं आपके साथ हूँ।"],
                 ["Mujhe batane ke liye thank you.", "Accha kiya jo aapne yeh bataya.", "Theek hai, main aapke saath hoon."],
                 ["ನನಗೆ ಹೇಳಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದಗಳು.", "ಇದನ್ನು ಹಂಚಿಕೊಂಡದ್ದು ಒಳ್ಳೆಯದು.", "ಸರಿ, ನಾನು ನಿಮ್ಮ ಜೊತೆ ಇದ್ದೇನೆ."]),
}

EXPLORE = L(["When you think {a}, what feels the heaviest?", "Tell me a bit more {a}. What's been happening lately?",
             "How long has this been on your mind?", "What part of this is weighing on you the most?"],
            ["{a} सोचते समय सबसे भारी क्या लगता है?", "{a} थोड़ा और बताइए। हाल ही में क्या-क्या हुआ?",
             "यह बात कितने समय से आपके मन में है?", "इसमें सबसे ज़्यादा क्या परेशान कर रहा है?"],
            ["{a} sochte waqt sabse bhaari kya lagta hai?", "{a} thoda aur bataiye. Haal hi mein kya kya hua?",
             "Yeh baat kitne time se aapke mann mein hai?", "Ismein sabse zyada kya pareshaan kar raha hai?"],
            ["{a} ಯೋಚಿಸಿದಾಗ ಅತ್ಯಂತ ಭಾರವಾಗಿ ಅನ್ನಿಸುವುದು ಯಾವುದು?", "{a} ಸ್ವಲ್ಪ ಹೆಚ್ಚು ಹೇಳಿ. ಇತ್ತೀಚೆಗೆ ಏನೇನು ನಡೆಯಿತು?",
             "ಇದು ಎಷ್ಟು ದಿನಗಳಿಂದ ನಿಮ್ಮ ಮನಸ್ಸಿನಲ್ಲಿದೆ?", "ಇದರಲ್ಲಿ ನಿಮಗೆ ಹೆಚ್ಚು ಕಾಡುತ್ತಿರುವುದು ಯಾವುದು?"])
# v3: situational, human follow-ups instead of "how do you feel?" questions
DEEPEN = L(["What happened most recently that made it feel this way?", "How have you been managing with all of it?",
            "What would make the next few hours even a little easier?", "Is there anyone around you who knows what you're dealing with?"],
           ["हाल ही में ऐसा क्या हुआ जिससे ऐसा लगने लगा?", "इन सब के साथ आप कैसे संभाल रहे हैं?",
            "अगले कुछ घंटे थोड़े आसान बनाने के लिए क्या मदद कर सकता है?", "क्या आसपास कोई है जिसे पता है कि आप किस दौर से गुज़र रहे हैं?"],
           ["Haal hi mein aisa kya hua jisse aisa lagne laga?", "In sab ke saath aap kaise sambhal rahe ho?",
            "Agle kuch ghante thode aasaan banane ke liye kya help kar sakta hai?", "Kya aas-paas koi hai jise pata hai ki aap kis daur se guzar rahe ho?"],
           ["ಇತ್ತೀಚೆಗೆ ಏನಾಯಿತು, ಹೀಗೆ ಅನ್ನಿಸಲು ಕಾರಣವಾಗಿದ್ದು?", "ಇದೆಲ್ಲವನ್ನೂ ಹೇಗೆ ನಿಭಾಯಿಸುತ್ತಿದ್ದೀರಿ?",
            "ಮುಂದಿನ ಕೆಲವು ಗಂಟೆಗಳನ್ನು ಸ್ವಲ್ಪ ಸುಲಭಗೊಳಿಸಲು ಏನು ಸಹಾಯ ಮಾಡಬಹುದು?", "ನೀವು ಏನನ್ನು ಎದುರಿಸುತ್ತಿದ್ದೀರಿ ಎಂದು ತಿಳಿದಿರುವವರು ಹತ್ತಿರ ಯಾರಾದರೂ ಇದ್ದಾರೆಯೇ?"])
CALLBACK = L("By the way, I was thinking about what you said earlier, {a}. Is that still on your mind?",
             "वैसे, आपने पहले {a} बताया था। क्या वो अब भी मन में है?",
             "Waise, aapne pehle {a} bataya tha. Kya woh abhi bhi mann mein hai?",
             "ಅಂದಹಾಗೆ, ನೀವು ಮೊದಲು {a} ಹೇಳಿದ್ದಿರಿ. ಅದು ಇನ್ನೂ ಮನಸ್ಸಿನಲ್ಲಿದೆಯಾ?")
CHOICE_CALM = L("Let's slow things down together. I've put a short exercise just below; go at your own pace and tell me how you feel after.",
                "चलिए साथ मिलकर थोड़ा धीमा करते हैं। नीचे एक छोटी एक्सरसाइज़ है, अपनी गति से कीजिए और बाद में बताइए कैसा लगा।",
                "Chalo saath milkar thoda dheema karte hain. Neeche ek chhoti exercise hai, apni speed se karo aur baad mein batao kaisa laga.",
                "ಒಟ್ಟಿಗೆ ಸ್ವಲ್ಪ ನಿಧಾನಿಸೋಣ. ಕೆಳಗೆ ಒಂದು ಸಣ್ಣ ವ್ಯಾಯಾಮವಿದೆ, ನಿಮ್ಮ ವೇಗದಲ್ಲಿ ಮಾಡಿ, ನಂತರ ಹೇಗನ್ನಿಸಿತು ಎಂದು ಹೇಳಿ.")
COPE = L(["What has helped you get through something like this before?", "Is there anyone you trust who knows what you're going through?",
          "What usually helps you, even a little, when you feel this way?"],
         ["पहले ऐसे समय में किस चीज़ ने आपकी मदद की थी?", "क्या कोई भरोसेमंद व्यक्ति है जिसे पता है कि आप क्या झेल रहे हैं?",
          "ऐसा महसूस होने पर थोड़ी सी भी राहत किस चीज़ से मिलती है?"],
         ["Pehle aise time mein kis cheez ne aapki help ki thi?", "Kya koi bharosemand insaan hai jise pata hai ki aap kya jhel rahe ho?",
          "Aisa feel hone par thodi si bhi raahat kis cheez se milti hai?"],
         ["ಹಿಂದೆ ಇಂತಹ ಸಮಯದಲ್ಲಿ ನಿಮಗೆ ಏನು ಸಹಾಯ ಮಾಡಿತ್ತು?", "ನೀವು ಏನನ್ನು ಎದುರಿಸುತ್ತಿದ್ದೀರಿ ಎಂದು ತಿಳಿದಿರುವ ನಂಬಿಕೆಯ ವ್ಯಕ್ತಿ ಯಾರಾದರೂ ಇದ್ದಾರೆಯೇ?",
          "ಹೀಗೆ ಅನ್ನಿಸಿದಾಗ ಸ್ವಲ್ಪವಾದರೂ ಸಮಾಧಾನ ಯಾವುದರಿಂದ ಸಿಗುತ್ತದೆ?"])
REFRAME = L(["What evidence do you have for that thought, and is there any evidence against it?",
             "If your best friend said that about themselves, what would you tell them?",
             "How true does that thought feel from 0 to 100, and would it be the same on a good day?"],
            ["उस विचार के पक्ष में क्या सबूत है, और क्या कुछ उसके ख़िलाफ़ भी है?",
             "अगर आपका सबसे अच्छा दोस्त अपने बारे में यही कहता, तो आप उससे क्या कहते?",
             "0 से 100 में वह विचार कितना सच लगता है, और क्या किसी अच्छे दिन भी उतना ही लगता?"],
            ["Us thought ke favour mein kya proof hai, aur kya kuch uske against bhi hai?",
             "Agar aapka best friend apne baare mein yahi kehta, toh aap usse kya kehte?",
             "0 se 100 mein woh thought kitna sach lagta hai, aur kya kisi acche din bhi utna hi lagta?"],
            ["ಆ ಯೋಚನೆಗೆ ಯಾವ ಆಧಾರವಿದೆ, ಮತ್ತು ಅದರ ವಿರುದ್ಧ ಏನಾದರೂ ಆಧಾರವಿದೆಯೇ?",
             "ನಿಮ್ಮ ಆತ್ಮೀಯ ಸ್ನೇಹಿತ ತನ್ನ ಬಗ್ಗೆ ಹೀಗೆ ಹೇಳಿದರೆ, ನೀವು ಅವರಿಗೆ ಏನು ಹೇಳುತ್ತೀರಿ?"])
SUMMARY = L(["We've talked through quite a bit. What would feel most helpful right now: talking it through more, a calming exercise, or a small plan for tomorrow?",
             "You've been carrying a lot. On a scale of 1 to 10, how are you feeling right now compared to when we started?"],
            ["हमने काफ़ी बातें कीं। अभी सबसे ज़्यादा मदद किस चीज़ से मिलेगी: और बात करना, कोई शांत करने वाली एक्सरसाइज़, या कल के लिए एक छोटा प्लान?",
             "आप बहुत कुछ उठा रहे हैं। 1 से 10 के पैमाने पर, शुरुआत की तुलना में अभी आप कैसा महसूस कर रहे हैं?"],
            ["Humne kaafi baatein ki. Abhi sabse zyada help kis cheez se milegi: aur baat karna, koi calming exercise, ya kal ke liye ek chhota plan?",
             "Aap bahut kuch utha rahe ho. 1 se 10 mein, shuru ke comparison mein abhi aap kaisa feel kar rahe ho?"],
            ["ನಾವು ಸಾಕಷ್ಟು ಮಾತನಾಡಿದೆವು. ಈಗ ನಿಮಗೆ ಹೆಚ್ಚು ಸಹಾಯವಾಗುವುದು ಯಾವುದು: ಇನ್ನಷ್ಟು ಮಾತನಾಡುವುದು, ಶಾಂತಗೊಳಿಸುವ ವ್ಯಾಯಾಮ, ಅಥವಾ ನಾಳೆಗಾಗಿ ಒಂದು ಸಣ್ಣ ಯೋಜನೆ?",
             "ನೀವು ತುಂಬಾ ಹೊತ್ತಿದ್ದೀರಿ. ನಾವು ಶುರುಮಾಡಿದಾಗಕ್ಕೆ ಹೋಲಿಸಿದರೆ, 1 ರಿಂದ 10 ರಲ್ಲಿ ಈಗ ನಿಮಗೆ ಹೇಗನ್ನಿಸುತ್ತಿದೆ?"])
SPACE = L(["Take your time. I'm right here.", "There's no rush. Say as much or as little as you like.",
           "Thank you for trusting me with this. I'm right here.", "That makes a lot of sense, given everything you've described."],
          ["आराम से बताइए, मैं यहीं हूँ।", "कोई जल्दी नहीं है। जितना चाहें उतना कहिए।", "मुझ पर भरोसा करने के लिए शुक्रिया। मैं यहीं हूँ।",
           "आपने जो बताया, उसके बाद ऐसा महसूस होना बिल्कुल समझ में आता है।"],
          ["Aaram se bataiye, main yahin hoon.", "Koi jaldi nahi hai. Jitna chahe utna kahiye.", "Mujh par bharosa karne ke liye thank you. Main yahin hoon.",
           "Aapne jo bataya, uske baad aisa feel hona bilkul samajh mein aata hai."],
          ["ನಿಧಾನವಾಗಿ ಹೇಳಿ, ನಾನು ಇಲ್ಲೇ ಇದ್ದೇನೆ.", "ಯಾವುದೇ ಆತುರವಿಲ್ಲ. ನಿಮಗೆ ಎಷ್ಟು ಬೇಕೋ ಅಷ್ಟು ಹೇಳಿ.", "ನನ್ನನ್ನು ನಂಬಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದ. ನಾನು ಇಲ್ಲೇ ಇದ್ದೇನೆ.",
           "ನೀವು ಹೇಳಿದ ಎಲ್ಲವನ್ನೂ ಗಮನಿಸಿದರೆ, ಹೀಗೆ ಅನ್ನಿಸುವುದು ಸಹಜ."])
# v3: no "pick a feeling word" questions - offer company or a lighter topic instead
UNSURE = L(["That's okay, we don't have to name it. Want to just tell me about your day, or talk about something completely different for a while?",
            "No pressure at all. Sometimes things feel heavy without a clear reason. I'm happy to keep you company either way.",
            "Fair enough, we can take it slow. What did you get up to today?"],
           ["कोई बात नहीं, हमें इसे कोई नाम देने की ज़रूरत नहीं। बस अपने दिन के बारे में बताइए, या थोड़ी देर कुछ बिल्कुल अलग बात करें?",
            "कोई दबाव नहीं। कभी-कभी बिना किसी साफ़ वजह के भी मन भारी लगता है। मैं हर हाल में आपके साथ हूँ।",
            "ठीक है, आराम से चलते हैं। आज दिन में क्या-क्या किया?"],
           ["Koi baat nahi, isse koi naam dene ki zaroorat nahi. Bas apne din ke baare mein batao, ya thodi der kuch bilkul alag baat karein?",
            "Koi pressure nahi. Kabhi kabhi bina kisi saaf wajah ke bhi mann bhaari lagta hai. Main har haal mein aapke saath hoon.",
            "Theek hai, aaram se chalte hain. Aaj din mein kya kya kiya?"],
           ["ಪರವಾಗಿಲ್ಲ, ಅದಕ್ಕೆ ಹೆಸರು ಕೊಡಬೇಕಿಲ್ಲ. ನಿಮ್ಮ ದಿನದ ಬಗ್ಗೆ ಹೇಳಿ, ಅಥವಾ ಸ್ವಲ್ಪ ಹೊತ್ತು ಬೇರೆ ಏನಾದರೂ ಮಾತನಾಡೋಣವೇ?",
            "ಯಾವುದೇ ಒತ್ತಡವಿಲ್ಲ. ಕೆಲವೊಮ್ಮೆ ಸ್ಪಷ್ಟ ಕಾರಣವಿಲ್ಲದೆಯೂ ಮನಸ್ಸು ಭಾರವಾಗುತ್ತದೆ. ಹೇಗಿದ್ದರೂ ನಾನು ನಿಮ್ಮ ಜೊತೆ ಇದ್ದೇನೆ.",
            "ಸರಿ, ನಿಧಾನವಾಗಿ ಹೋಗೋಣ. ಇಂದು ಏನೇನು ಮಾಡಿದಿರಿ?"])
AFFIRM_EXERCISE = L(["Wonderful. Go at your own pace with the card above, and tell me how you feel afterwards.",
                     "Great. There's no right or wrong way to do it. I'll be here when you're done."],
                    ["बहुत बढ़िया। ऊपर दिए कार्ड के साथ अपनी गति से कीजिए, और बाद में बताइए कि कैसा लगा।",
                     "बढ़िया। इसे करने का कोई सही या गलत तरीका नहीं है। जब हो जाए, मैं यहीं हूँ।"],
                    ["Bahut badhiya. Upar wale card ke saath apni speed se kijiye, aur baad mein bataiye kaisa laga.",
                     "Badhiya. Isse karne ka koi sahi ya galat tareeka nahi hai. Jab ho jaaye, main yahin hoon."],
                    ["ತುಂಬಾ ಒಳ್ಳೆಯದು. ಮೇಲಿನ ಕಾರ್ಡ್‌ನೊಂದಿಗೆ ನಿಮ್ಮದೇ ವೇಗದಲ್ಲಿ ಮಾಡಿ, ನಂತರ ಹೇಗನ್ನಿಸಿತು ಎಂದು ಹೇಳಿ.",
                     "ಒಳ್ಳೆಯದು. ಇದನ್ನು ಮಾಡಲು ಸರಿ ಅಥವಾ ತಪ್ಪು ವಿಧಾನವಿಲ್ಲ. ಮುಗಿದಾಗ ನಾನು ಇಲ್ಲೇ ಇರುತ್ತೇನೆ."])
DENY_EXERCISE = L(["That's completely okay. We can just talk. What's on your mind right now?",
                   "No problem at all. I'm happy to simply listen. What would you like to talk about?"],
                  ["बिल्कुल ठीक है। हम बस बात कर सकते हैं। अभी आपके मन में क्या चल रहा है?",
                   "कोई बात नहीं। मैं बस सुनने के लिए भी यहाँ हूँ। आप किस बारे में बात करना चाहेंगे?"],
                  ["Bilkul theek hai. Hum bas baat kar sakte hain. Abhi aapke mann mein kya chal raha hai?",
                   "Koi baat nahi. Main bas sunne ke liye bhi yahan hoon. Aap kis baare mein baat karna chahenge?"],
                  ["ಪರವಾಗಿಲ್ಲ. ನಾವು ಸುಮ್ಮನೆ ಮಾತನಾಡಬಹುದು. ಈಗ ನಿಮ್ಮ ಮನಸ್ಸಿನಲ್ಲಿ ಏನಿದೆ?",
                   "ಯಾವುದೇ ತೊಂದರೆಯಿಲ್ಲ. ಕೇಳಲು ನಾನು ಇಲ್ಲಿದ್ದೇನೆ. ನೀವು ಯಾವುದರ ಬಗ್ಗೆ ಮಾತನಾಡಲು ಬಯಸುತ್ತೀರಿ?"])
AFFIRM = L(["Okay. Tell me a little more, whatever comes to mind first.", "Go on. What comes up when you think about it?"],
           ["ठीक है। थोड़ा और बताइए, जो भी सबसे पहले मन में आए।", "बताइए, जब आप इसके बारे में सोचते हैं तो क्या महसूस होता है?"],
           ["Theek hai. Thoda aur bataiye, jo bhi sabse pehle mann mein aaye.", "Bataiye, jab aap iske baare mein sochte ho toh kya feel hota hai?"],
           ["ಸರಿ. ಮೊದಲು ಮನಸ್ಸಿಗೆ ಬಂದದ್ದನ್ನು ಸ್ವಲ್ಪ ಹೆಚ್ಚು ಹೇಳಿ.", "ಹೇಳಿ, ಅದರ ಬಗ್ಗೆ ಯೋಚಿಸಿದಾಗ ನಿಮಗೆ ಏನನ್ನಿಸುತ್ತದೆ?"])
DENY = L(["That's okay. We can go wherever feels right for you.", "Fair enough. What would you rather talk about?"],
         ["ठीक है। जहाँ आपको सही लगे, बात वहीं ले चलते हैं।", "कोई बात नहीं। आप किस बारे में बात करना चाहेंगे?"],
         ["Theek hai. Jahan aapko sahi lage, baat wahin le chalte hain.", "Koi baat nahi. Aap kis baare mein baat karna chahoge?"],
         ["ಪರವಾಗಿಲ್ಲ. ನಿಮಗೆ ಸರಿ ಅನ್ನಿಸುವ ಕಡೆ ಮಾತು ಮುಂದುವರಿಸೋಣ.", "ಸರಿ. ನೀವು ಯಾವುದರ ಬಗ್ಗೆ ಮಾತನಾಡಲು ಇಷ್ಟಪಡುತ್ತೀರಿ?"])
AFFIRM_COUNSELOR = L("I'm glad. Press 'Talk to a counsellor' below and someone from the care team will reach out to you.",
                     "अच्छा फ़ैसला। नीचे 'Talk to a counsellor' दबाइए, केयर टीम से कोई आपसे संपर्क करेगा।",
                     "Accha decision. Neeche 'Talk to a counsellor' dabaiye, care team se koi aapse contact karega.",
                     "ಒಳ್ಳೆಯ ನಿರ್ಧಾರ. ಕೆಳಗಿನ 'Talk to a counsellor' ಒತ್ತಿ, ಕೇರ್ ತಂಡದಿಂದ ಯಾರಾದರೂ ನಿಮ್ಮನ್ನು ಸಂಪರ್ಕಿಸುತ್ತಾರೆ.")
COUNSELOR_OFFER = L(["It seems things have felt heavy for a while. Would it help to talk to a counsellor? There's a button just below.",
                     "You don't have to carry this alone. A short check-in or a chat with a counsellor are both one tap away below."],
                    ["लगता है कुछ समय से सब भारी लग रहा है। क्या किसी काउंसलर से बात करना मदद करेगा? नीचे बटन है।",
                     "आपको यह अकेले नहीं उठाना है। नीचे एक क्लिक में चेक-इन या काउंसलर से बात हो सकती है।"],
                    ["Lagta hai kuch time se sab bhaari lag raha hai. Kya kisi counsellor se baat karna help karega? Neeche button hai.",
                     "Aapko yeh akele nahi uthana hai. Neeche ek click mein check-in ya counsellor se baat ho sakti hai."],
                    ["ಸ್ವಲ್ಪ ಸಮಯದಿಂದ ಎಲ್ಲವೂ ಭಾರವಾಗಿ ಅನ್ನಿಸುತ್ತಿದೆ ಎಂದು ತೋರುತ್ತದೆ. ಕೌನ್ಸೆಲರ್ ಜೊತೆ ಮಾತನಾಡುವುದು ಸಹಾಯ ಮಾಡಬಹುದೇ? ಕೆಳಗೆ ಬಟನ್ ಇದೆ.",
                     "ಇದನ್ನು ನೀವು ಒಬ್ಬರೇ ಹೊರಬೇಕಿಲ್ಲ. ಕೆಳಗೆ ಒಂದು ಕ್ಲಿಕ್‌ನಲ್ಲಿ ಚೆಕ್-ಇನ್ ಅಥವಾ ಕೌನ್ಸೆಲರ್ ಜೊತೆ ಮಾತು ಸಾಧ್ಯ."])
HELP_INTRO = L("Let's find one small next step together.", "चलिए साथ मिलकर एक छोटा अगला कदम ढूँढते हैं।",
               "Chaliye saath milkar ek chhota next step dhoondhte hain.", "ಬನ್ನಿ, ಒಟ್ಟಿಗೆ ಒಂದು ಸಣ್ಣ ಮುಂದಿನ ಹೆಜ್ಜೆ ಹುಡುಕೋಣ.")
TIP_CHECK = L(["How does that sound to you?", "Would something like that work for you?"],
              ["यह आपको कैसा लगता है?", "क्या ऐसा कुछ आपके लिए काम करेगा?"],
              ["Yeh aapko kaisa lagta hai?", "Kya aisa kuch aapke liye kaam karega?"],
              ["ಇದು ನಿಮಗೆ ಹೇಗನ್ನಿಸುತ್ತದೆ?", "ಇಂತಹದ್ದು ನಿಮಗೆ ಸರಿಹೊಂದಬಹುದೇ?"])
BETTER = L(["I'm really glad to hear that. What do you think helped?", "That's lovely to hear. What would help you hold on to this feeling?"],
           ["यह सुनकर सच में खुशी हुई। आपको क्या लगता है, किस चीज़ ने मदद की?", "बहुत अच्छा लगा सुनकर। इस एहसास को बनाए रखने में क्या मदद करेगा?"],
           ["Yeh sunkar sach mein khushi hui. Aapko kya lagta hai, kis cheez ne help ki?", "Bahut accha laga sunkar. Is feeling ko banaye rakhne mein kya help karega?"],
           ["ಇದನ್ನು ಕೇಳಿ ನಿಜವಾಗಿಯೂ ಸಂತೋಷವಾಯಿತು. ಯಾವುದು ಸಹಾಯ ಮಾಡಿತು ಅನ್ನಿಸುತ್ತದೆ?", "ಕೇಳಿ ಖುಷಿಯಾಯಿತು. ಈ ಭಾವನೆಯನ್ನು ಉಳಿಸಿಕೊಳ್ಳಲು ಏನು ಸಹಾಯ ಮಾಡುತ್ತದೆ?"])
GREET = L(["Hi, I'm {name}. I'm here to listen, without judgement. How are you feeling today?",
           "Hello! It's good to see you. What's on your mind right now?"],
          ["नमस्ते, मैं {name} हूँ। मैं बिना किसी जजमेंट के आपकी बात सुनने के लिए यहाँ हूँ। आज आप कैसा महसूस कर रहे हैं?",
           "नमस्ते! आपसे मिलकर अच्छा लगा। अभी आपके मन में क्या चल रहा है?"],
          ["Namaste, main {name} hoon. Main bina judge kiye aapki baat sunne ke liye yahan hoon. Aaj aap kaisa feel kar rahe ho?",
           "Hello! Aapse milkar accha laga. Abhi aapke mann mein kya chal raha hai?"],
          ["ನಮಸ್ಕಾರ, ನಾನು {name}. ಯಾವುದೇ ತೀರ್ಪು ಇಲ್ಲದೆ ನಿಮ್ಮ ಮಾತು ಕೇಳಲು ಇಲ್ಲಿದ್ದೇನೆ. ಇಂದು ನಿಮಗೆ ಹೇಗನ್ನಿಸುತ್ತಿದೆ?",
           "ನಮಸ್ಕಾರ! ನಿಮ್ಮನ್ನು ನೋಡಿ ಖುಷಿಯಾಯಿತು. ಈಗ ನಿಮ್ಮ ಮನಸ್ಸಿನಲ್ಲಿ ಏನಿದೆ?"])
THANKS_R = L(["You're welcome. I'm here whenever you want to talk.", "Anytime. Thank you for trusting me with this."],
             ["कोई बात नहीं। जब भी बात करनी हो, मैं यहाँ हूँ।", "हमेशा। मुझ पर भरोसा करने के लिए धन्यवाद।"],
             ["Koi baat nahi. Jab bhi baat karni ho, main yahan hoon.", "Hamesha. Mujh par bharosa karne ke liye thank you."],
             ["ಪರವಾಗಿಲ್ಲ. ಮಾತನಾಡಬೇಕೆನಿಸಿದಾಗ ನಾನು ಇಲ್ಲಿದ್ದೇನೆ.", "ಯಾವಾಗಲೂ. ನನ್ನನ್ನು ನಂಬಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದಗಳು."])
BYE_R = L(["Take care of yourself. A short check-in tomorrow might help you notice how you're doing.",
           "Goodbye for now. Be gentle with yourself tonight."],
          ["अपना ध्यान रखिए। कल एक छोटा-सा चेक-इन आपको अपनी हालत समझने में मदद करेगा।", "फिर मिलते हैं। आज रात खुद के साथ नरमी से पेश आइए।"],
          ["Apna dhyaan rakhiye. Kal ek chhota sa check-in aapko apni haalat samajhne mein help karega.", "Phir milte hain. Aaj raat khud ke saath narmi se pesh aaiye."],
          ["ನಿಮ್ಮನ್ನು ನೋಡಿಕೊಳ್ಳಿ. ನಾಳೆ ಒಂದು ಸಣ್ಣ ಚೆಕ್-ಇನ್ ನಿಮ್ಮ ಸ್ಥಿತಿ ಅರಿಯಲು ಸಹಾಯ ಮಾಡುತ್ತದೆ.", "ಮತ್ತೆ ಸಿಗೋಣ. ಇಂದು ರಾತ್ರಿ ನಿಮ್ಮೊಂದಿಗೆ ಮೃದುವಾಗಿರಿ."])
EXERCISE_OFFER = {
    "box_breathing": L("Would you like to try a one-minute box breathing exercise with me? It's just below.",
                       "क्या आप मेरे साथ एक मिनट की बॉक्स ब्रीदिंग करना चाहेंगे? यह नीचे दी गई है।",
                       "Kya aap mere saath ek minute ki box breathing try karna chahenge? Neeche card hai.",
                       "ನನ್ನ ಜೊತೆ ಒಂದು ನಿಮಿಷದ ಬಾಕ್ಸ್ ಬ್ರೀದಿಂಗ್ ಮಾಡಲು ಬಯಸುತ್ತೀರಾ? ಅದು ಕೆಳಗಿದೆ."),
    "grounding": L("If it feels like too much, the 5-4-3-2-1 grounding exercise below can bring you back to the present. Want to try it?",
                   "अगर सब कुछ बहुत ज़्यादा लग रहा है, तो नीचे दी गई 5-4-3-2-1 ग्राउंडिंग एक्सरसाइज़ आपको वर्तमान में लौटा सकती है। आज़माना चाहेंगे?",
                   "Agar sab bahut zyada lag raha hai, toh neeche wali 5-4-3-2-1 grounding exercise madad kar sakti hai. Try karein?",
                   "ಎಲ್ಲವೂ ಅತಿಯಾಗಿ ಅನ್ನಿಸಿದರೆ, ಕೆಳಗಿನ 5-4-3-2-1 ಗ್ರೌಂಡಿಂಗ್ ವ್ಯಾಯಾಮ ನಿಮ್ಮನ್ನು ಈ ಕ್ಷಣಕ್ಕೆ ತರಬಹುದು. ಪ್ರಯತ್ನಿಸುತ್ತೀರಾ?"),
    "thought_record": L("Writing the thought down and looking at it like a fair friend can loosen its grip. Want to try the thought record below?",
                        "उस विचार को लिखकर एक समझदार दोस्त की तरह देखने से उसकी पकड़ ढीली हो सकती है। नीचे दिया थॉट रिकॉर्ड आज़माएँगे?",
                        "Us thought ko likh kar ek samajhdaar dost ki tarah dekhne se uski pakad dheeli ho sakti hai. Neeche wala thought record try karein?",
                        "ಆ ಯೋಚನೆಯನ್ನು ಬರೆದು ಒಬ್ಬ ನ್ಯಾಯಯುತ ಸ್ನೇಹಿತನಂತೆ ನೋಡಿದರೆ ಅದರ ಹಿಡಿತ ಕಡಿಮೆಯಾಗಬಹುದು. ಕೆಳಗಿನ ಥಾಟ್ ರೆಕಾರ್ಡ್ ಪ್ರಯತ್ನಿಸುತ್ತೀರಾ?"),
    "small_step": L("Sometimes one tiny action helps more than a big plan. Want to pick a small step from the card below?",
                    "कभी-कभी एक छोटा-सा कदम बड़े प्लान से ज़्यादा मदद करता है। नीचे से एक छोटा कदम चुनना चाहेंगे?",
                    "Kabhi kabhi ek chhota sa step bade plan se zyada help karta hai. Neeche card se ek chhota step chunna chahenge?",
                    "ಕೆಲವೊಮ್ಮೆ ಒಂದು ಸಣ್ಣ ಹೆಜ್ಜೆ ದೊಡ್ಡ ಯೋಜನೆಗಿಂತ ಹೆಚ್ಚು ಸಹಾಯ ಮಾಡುತ್ತದೆ. ಕೆಳಗಿನ ಕಾರ್ಡ್‌ನಿಂದ ಒಂದು ಸಣ್ಣ ಹೆಜ್ಜೆ ಆರಿಸುತ್ತೀರಾ?"),
}

# --------------------------------------------------------------------------- intents
GREETING = re.compile(r"^\s*(hi+|hello+|hey+|namaste|namaskar|good (morning|afternoon|evening)|नमस्ते|नमस्कार|ನಮಸ್ಕಾರ|ಹಾಯ್)[\s!.]*$", re.I)
THANKS = re.compile(r"\b(thanks?|thank you|thx|shukriya|dhanyavad)\b|धन्यवाद|शुक्रिया|ಧನ್ಯವಾದ", re.I)
BYE = re.compile(r"\b(bye|goodbye|good night|see you|gotta go|talk later|chalta hoon|chalti hoon)\b|अलविदा|फिर मिलते|ಹೋಗಿ ಬರುತ್ತೇನೆ", re.I)
# (?=...) instead of \b: Python's \b fails after Devanagari/Kannada vowel signs (हाँ, नहीं, ಹೌದು)
_END = r"(?=[\s.,!?।]|$)"
AFFIRM_RE = re.compile(r"^\s*(yes|yeah|yep|yup|sure|ok|okay|alright|of course|haan|han|ha|ji|ji haan|theek hai|thik hai|"
                       r"हाँ|हां|जी|जी हाँ|ठीक है|ಹೌದು|ಸರಿ)" + _END, re.I)
DENY_RE = re.compile(r"^\s*(no|nope|nah|not really|not now|nahi|nahin|nhi|na|नहीं|ना|जी नहीं|ಇಲ್ಲ|ಬೇಡ)" + _END, re.I)
UNSURE_RE = re.compile(r"\b(i dont know|i do not know|idk|not sure|no idea|dunno|pata nahi|pata nhi|maloom nahi)\b|पता नहीं|ಗೊತ್ತಿಲ್ಲ", re.I)
HELP_RE = re.compile(r"\b(what should i do|what do i do|help me|any (advice|tips)|how (do|can) i|kya karu|kya karun|kya karoon)\b"
                     r"|क्या करूँ|क्या करूं|मदद कर|ಏನು ಮಾಡಲಿ|ಸಹಾಯ ಮಾಡಿ", re.I)
BETTER_RE = re.compile(r"\b(feeling better|feel better|i am better|im better|much better|feel good|feeling good|better now|"
                       r"accha lag raha|acha lag raha|behtar)\b|बेहतर|अच्छा लग रहा|ಚೆನ್ನಾಗಿದೆ|ಉತ್ತಮ", re.I)
NEGATED = re.compile(r"\b(not|nahi|nahin|nhi)\b|नहीं|ಇಲ್ಲ", re.I)
FEEL = re.compile(r"\bi(?: am|m)? (?:feel|feeling)(?: like)? (?:so |really |very |quite |kind of |a bit |a little )?"
                  r"([a-z][a-z \-]{2,40}?)(?:[.,!?]|$| because| and| but| about| when)", re.I)
_SWAP = {"my": "your", "me": "you", "i": "you", "im": "you're", "myself": "yourself", "mine": "yours", "am": "are"}


def _norm(text: str) -> str:
    return text.lower().replace("'", "").replace("’", "").strip()


def detect_topic(text: str) -> str | None:
    t = _norm(text)
    for name, pat in TOPIC_PATTERNS.items():
        if re.search(rf"(?<![a-z])({pat})", t):
            return name
    return None


def choose_exercise(topic: str | None, emotion: str, distress: float) -> str | None:
    if topic == "panic" or (emotion == "fear" and distress >= 0.55):
        return "box_breathing"
    if topic in {"overthinking", "selfworth"}:
        return "thought_record"
    if emotion == "fear" and distress >= 0.4:
        return "grounding"
    if emotion == "sadness" and distress >= 0.5:
        return "small_step"
    return None


def _pick(pool: dict, lang: str, mem: dict, **fmt) -> str:
    """Pick a sentence never used in this session (falls back to least-recent)."""
    options = pool.get(lang) or pool["en"]
    used: list = mem.setdefault("used", [])
    fresh = [o for o in options if o not in used]
    choice = random.choice(fresh) if fresh else min(options, key=used.index)
    if choice in used:
        used.remove(choice)
    used.append(choice)
    return choice.format(name=config.COMPANION_NAME, **fmt)


def _pick_fresh(pool: dict, lang: str, mem: dict) -> str | None:
    """Like _pick but returns None instead of repeating."""
    options = pool.get(lang) or pool["en"]
    used: list = mem.setdefault("used", [])
    fresh = [o for o in options if o not in used]
    if not fresh:
        return None
    choice = random.choice(fresh)
    used.append(choice)
    return choice


def _reflect_phrase(text: str) -> str | None:
    m = FEEL.search(text)
    if not m:
        return None
    phrase = " ".join(_SWAP.get(w, w) for w in m.group(1).strip().lower().split())
    if len(phrase) < 3 or phrase in {"good", "fine", "ok", "okay", "great", "better"}:
        return None
    return f"It sounds like you're feeling {phrase}."


def greeting(lang: str, mem: dict) -> str:
    return _pick(GREET, lang, mem)


def respond(text: str, emotion: str, distress: float, tier: str, memory: dict, lang: str = "en") -> dict:
    """Return {"reply", "exercise", "topic", "intent"}; memory carries session state."""
    lang = lang if lang in LANGS else "en"
    mem = memory
    mem["turn"] = mem.get("turn", 0) + 1
    clean = _norm(text)              # lower-case, apostrophes removed ("don't" -> "dont")
    words = len(clean.split())
    last_q = mem.get("last_q")

    def out(reply: str, intent: str, exercise: str | None = None, topic: str | None = None) -> dict:
        return {"reply": reply, "exercise": exercise, "topic": topic or mem.get("topic"), "intent": intent}

    # ---------- short conversational intents ----------
    if GREETING.match(clean):
        mem["last_q"] = "open"
        return out(_pick(GREET, lang, mem), "greeting")
    if THANKS.search(clean) and words <= 6:
        mem["last_q"] = None
        return out(_pick(THANKS_R, lang, mem), "thanks")
    if BYE.search(clean) and words <= 6:
        mem["last_q"] = None
        return out(_pick(BYE_R, lang, mem), "bye")
    if words <= 4 and AFFIRM_RE.match(clean):
        if last_q == "exercise":
            mem["last_q"] = None
            return out(_pick(AFFIRM_EXERCISE, lang, mem), "affirm")
        if last_q == "counselor":
            mem["last_q"] = None
            return out(_pick(AFFIRM_COUNSELOR, lang, mem), "affirm")
        mem["last_q"] = "open"
        return out(_pick(AFFIRM, lang, mem), "affirm")
    if words <= 4 and DENY_RE.match(clean):
        if last_q == "exercise" and mem.get("last_exercise"):
            mem.setdefault("declined", []).append(mem["last_exercise"])
            mem["last_q"] = "open"
            return out(_pick(DENY_EXERCISE, lang, mem), "deny")
        mem["last_q"] = "open"
        return out(_pick(DENY, lang, mem), "deny")
    # ---------- answer to "vent / distract / calm?" ----------
    if last_q == "choice":
        for choice, rx in st.CHOICE_RE.items():
            if rx.search(clean):
                mem["last_q"] = "open"
                mem["vague"] = 0
                if choice == "calm":
                    ex = next((e for e in ("grounding", "box_breathing", "small_step") if e not in mem.setdefault("offered", [])), "box_breathing")
                    mem["offered"].append(ex)
                    mem["exercise_turn"] = mem["turn"]
                    return out(_pick(CHOICE_CALM, lang, mem), "choice", ex)
                return out(_pick(st.CHOICE_VENT if choice == "vent" else st.CHOICE_DISTRACT, lang, mem), "choice")

    def offer_choice() -> dict:
        mem["last_q"] = "choice"
        mem["vague"] = 0
        return out(_pick(st.OFFER_CHOICE, lang, mem), "offer_choice")

    if UNSURE_RE.search(clean) and words <= 8:
        mem["vague"] = mem.get("vague", 0) + 1
        if mem["vague"] >= 2:
            return offer_choice()
        mem["last_q"] = "open"
        return out(_pick(UNSURE, lang, mem), "unsure")
    if BETTER_RE.search(clean) and not NEGATED.search(clean):
        mem["last_q"] = "open"
        return out(_pick(BETTER, lang, mem), "better")

    # ---------- feeling low: ask what happened ONCE, then offer a choice ----------
    if st.LOW_MOOD_RE.search(clean) and not detect_topic(clean):
        if mem.get("low_mood_asked"):
            return offer_choice()
        mem["low_mood_asked"] = True
        mem["last_q"] = "open"
        return out(_pick(st.LOW_MOOD, lang, mem), "low_mood")

    # ---------- casual conversation ----------
    small = st.detect(clean)
    if small and (words <= 10 or small in {"who_are_you", "joke"}):
        if small == "filler":
            if last_q in {"open", None}:
                mem["vague"] = mem.get("vague", 0) + 1
                if mem["vague"] >= 3:
                    return offer_choice()
            mem["last_q"] = "open"
        else:
            mem["vague"] = 0
            mem["last_q"] = "open"
        reply = _pick(st.POOLS[small], lang, mem)
        mem["small_turns"] = mem.get("small_turns", 0) + 1
        return out(reply, small)
    hobby = st.interest(clean)
    if hobby and emotion in {"joy", "neutral", "surprise"} and distress < 0.45 and not detect_topic(clean):
        mem["vague"] = 0
        mem["last_q"] = "open"
        seen = mem.setdefault("interests", [])
        pool = st.INTEREST_FOLLOW if hobby in seen else st.INTERESTS[hobby][1]
        seen.append(hobby)
        mem["small_turns"] = mem.get("small_turns", 0) + 1
        return out(_pick(pool, lang, mem), "interest")
    mem["vague"] = 0

    # ---------- content message: staged, non-repeating ----------
    topic = detect_topic(clean) or mem.get("topic")
    if topic != mem.get("topic"):
        mem["topic"] = topic
    stages: dict = mem.setdefault("stage", {})
    key = topic or "_general"
    stage = stages.get(key, 0)
    a = _pick_about(topic, lang)
    parts: list[str] = []

    # Reflection: their own words first, then an unused emotion line, then an unused
    # neutral line - and if every reflection has been used, none (never a repeat).
    reflection = _reflect_phrase(text) if lang == "en" else None
    if reflection and reflection not in mem.setdefault("used", []):
        mem["used"].append(reflection)
        parts.append(reflection)
    else:
        line = _pick_fresh(REFLECT.get(emotion, REFLECT["neutral"]), lang, mem) \
            or _pick_fresh(REFLECT["neutral"], lang, mem)
        if line:
            parts.append(line)

    if stage == 0 and topic in VALIDATE and emotion != "joy":
        parts.append(_pick(VALIDATE[topic], lang, mem))

    asking_for_help = bool(HELP_RE.search(clean))
    exercise = None
    candidate = choose_exercise(topic, emotion, distress)
    offered: list = mem.setdefault("offered", [])
    recently = mem["turn"] - mem.get("exercise_turn", -99) < 3
    if candidate and candidate not in offered and candidate not in mem.get("declined", []) and not recently \
            and (stage >= 1 or topic == "panic" or asking_for_help):
        exercise = candidate
        offered.append(candidate)
        mem["exercise_turn"] = mem["turn"]
        mem["last_exercise"] = candidate

    counselor_due = tier == "MEDIUM" and mem["turn"] - mem.get("counselor_turn", -99) >= 4
    if asking_for_help:
        parts.append(_pick(HELP_INTRO, lang, mem))

    if counselor_due:
        parts.append(_pick(COUNSELOR_OFFER, lang, mem))
        mem["counselor_turn"] = mem["turn"]
        mem["last_q"] = "counselor"
    elif exercise:
        parts.append(_pick(EXERCISE_OFFER[exercise], lang, mem))
        mem["last_q"] = "exercise"
    elif asking_for_help or stage == 3:
        parts.append(_pick(TIPS.get(topic, TIPS[None]), lang, mem))
        parts.append(_pick(TIP_CHECK, lang, mem))
        mem["last_q"] = "open"
    elif emotion == "joy":
        parts.append(_pick(L(["What made it feel good?", "How can you hold on to a bit of this feeling?"],
                             ["किस बात से इतना अच्छा लगा?", "इस एहसास को थोड़ा और कैसे बनाए रखें?"],
                             ["Kis baat se itna accha laga?", "Is feeling ko thoda aur kaise banaye rakhein?"],
                             ["ಯಾವುದರಿಂದ ಇಷ್ಟು ಖುಷಿಯಾಯಿತು?", "ಈ ಭಾವನೆಯನ್ನು ಸ್ವಲ್ಪ ಹೆಚ್ಚು ಹೇಗೆ ಉಳಿಸಿಕೊಳ್ಳಬಹುದು?"]), lang, mem))
        mem["last_q"] = "open"
    elif (mem["turn"] % 3 == 0 and stage > 0) or len(clean.split()) >= 25:
        parts.append(_pick(SPACE, lang, mem))        # hold space - no question this turn
        mem["last_q"] = None
    elif mem.get("small_turns", 0) >= 3 and topic and not mem.get("called_back") and not detect_topic(clean):
        parts.append(_pick(CALLBACK, lang, mem, a=a))  # human-like callback to an earlier topic
        mem["called_back"] = True
        mem["last_q"] = "open"
    else:
        if stage == 0:
            pool = EXPLORE
        elif stage == 1:
            pool = DEEPEN
        elif stage == 2:
            pool = REFRAME if topic in {"overthinking", "selfworth"} else COPE
        else:
            pool = SUMMARY if stage == 4 else random.choice([EXPLORE, DEEPEN, COPE])
        parts.append(_pick(pool, lang, mem, a=a))
        mem["last_q"] = "open"

    stages[key] = stage + 1
    return out(" ".join(parts), "content", exercise, topic)


def _pick_about(topic: str | None, lang: str) -> str:
    return (ABOUT.get(topic) or ABOUT[None])[lang][0]
