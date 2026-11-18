"""Casual, human-style conversation for the offline engine (four languages).

v2 could only "do therapy": every message got reflect + validate + a question about
feelings, so ordinary chat ("how are you?", "I'm bored", "I watched a movie")
turned into an interview and the conversation died. This module lets the
companion behave like a warm friend: answer questions about itself, joke,
talk about interests, accept "nothing much", and - when someone feels low -
ask what happened ONCE and then offer a choice instead of more feeling-questions.
"""
from __future__ import annotations

import re

from .i18n import L

# --------------------------------------------------------------------------- about itself
HOW_ARE_YOU = L(
    ["I'm doing well, thank you for asking! Talking with you is honestly the best part of my day. How's your day been so far?",
     "Pretty good, thanks! I've been right here, ready for a chat. What about you, how are things?",
     "I'm good! It's nice when someone asks me that. How are you doing, really?"],
    ["मैं ठीक हूँ, पूछने के लिए शुक्रिया! आपसे बात करना सच में अच्छा लगता है। आपका दिन कैसा जा रहा है?",
     "सब बढ़िया है, धन्यवाद! बस आपसे बात करने का इंतज़ार था। आप बताइए, कैसा चल रहा है?",
     "सब बढ़िया है! जब कोई यह पूछता है तो अच्छा लगता है। आप सच में कैसे हैं?"],
    ["Main theek hoon, poochne ke liye thank you! Aapse baat karna sach mein accha lagta hai. Aapka din kaisa ja raha hai?",
     "Badhiya, thank you! Bas aapse baat karne ka wait tha. Aap batao, kaisa chal raha hai?",
     "Sab badhiya hai! Jab koi yeh poochta hai toh accha lagta hai. Aap sach mein kaise ho?"],
    ["ನಾನು ಚೆನ್ನಾಗಿದ್ದೇನೆ, ಕೇಳಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದಗಳು! ನಿಮ್ಮ ಜೊತೆ ಮಾತನಾಡುವುದು ನಿಜವಾಗಿಯೂ ಖುಷಿ ಕೊಡುತ್ತದೆ. ನಿಮ್ಮ ದಿನ ಹೇಗೆ ಸಾಗುತ್ತಿದೆ?",
     "ಚೆನ್ನಾಗಿದೆ, ಧನ್ಯವಾದ! ನಿಮ್ಮ ಜೊತೆ ಮಾತನಾಡಲು ಕಾಯುತ್ತಿದ್ದೆ. ನೀವು ಹೇಳಿ, ಹೇಗಿದೆ?"])

WHO_ARE_YOU = L(
    ["I'm {name}, an AI companion made to listen. My name means 'connection' in Sanskrit, which is kind of my whole job: being here when you want to talk, and helping you reach real people when you need them. What's on your mind today?",
     "I'm {name}! Think of me as a friend who's always awake: no judgement, no hurry. I'm an AI, so I can't replace a real counsellor, but I'm good company. What would you like to talk about?"],
    ["मैं {name} हूँ, एक AI साथी जो आपकी बात सुनने के लिए बना है। संस्कृत में मेरे नाम का मतलब है 'जुड़ाव', और यही मेरा काम है: जब आप बात करना चाहें तब साथ रहना, और ज़रूरत पड़ने पर आपको असली लोगों से जोड़ना। आज आपके मन में क्या है?",
     "मैं {name} हूँ! मुझे एक ऐसा दोस्त समझिए जो हमेशा जागता रहता है, बिना जजमेंट और बिना जल्दबाज़ी के। मैं AI हूँ, काउंसलर की जगह तो नहीं, पर बातचीत के लिए हमेशा हाज़िर हूँ। आप किस बारे में बात करना चाहेंगे?"],
    ["Main {name} hoon, ek AI saathi jo aapki baat sunne ke liye bana hai. Sanskrit mein mere naam ka matlab hai 'connection', aur yahi mera kaam hai: jab aap baat karna chaho tab saath rehna, aur zaroorat pade toh aapko asli logon se jodna. Aaj mann mein kya hai?",
     "Main {name} hoon! Mujhe ek aisa dost samjho jo hamesha jaagta hai, bina judge kiye, bina jaldi ke. Main AI hoon, counsellor ki jagah toh nahi, par baat karne ke liye hamesha haazir hoon. Kis baare mein baat karein?"],
    ["ನಾನು {name}, ನಿಮ್ಮ ಮಾತು ಕೇಳಲು ಮಾಡಿದ AI ಸಂಗಾತಿ. ಸಂಸ್ಕೃತದಲ್ಲಿ ನನ್ನ ಹೆಸರಿನ ಅರ್ಥ 'ಸಂಪರ್ಕ', ಅದೇ ನನ್ನ ಕೆಲಸ: ನೀವು ಮಾತನಾಡಬೇಕೆಂದಾಗ ಜೊತೆಗಿರುವುದು, ಅಗತ್ಯವಿದ್ದಾಗ ನಿಜವಾದ ಜನರೊಂದಿಗೆ ಜೋಡಿಸುವುದು. ಇಂದು ನಿಮ್ಮ ಮನಸ್ಸಿನಲ್ಲಿ ಏನಿದೆ?"])

ARE_YOU_HUMAN = L(
    "I'm an AI, not a person, and I'll always be honest about that. But I'm genuinely here to listen, and I remember what you've told me in this conversation.",
    "मैं एक AI हूँ, इंसान नहीं, और यह बात हमेशा साफ़ रहेगी। लेकिन आपकी बात सुनने के लिए मैं सच में यहाँ हूँ, और इस बातचीत में आपने जो बताया वह मुझे याद है।",
    "Main ek AI hoon, insaan nahi, aur yeh baat hamesha saaf rahegi. Lekin aapki baat sunne ke liye main sach mein yahan hoon, aur is baatcheet mein aapne jo bataya woh mujhe yaad hai.",
    "ನಾನು AI, ಮನುಷ್ಯನಲ್ಲ, ಅದನ್ನು ಯಾವಾಗಲೂ ಪ್ರಾಮಾಣಿಕವಾಗಿ ಹೇಳುತ್ತೇನೆ. ಆದರೆ ನಿಮ್ಮ ಮಾತು ಕೇಳಲು ನಿಜವಾಗಿಯೂ ಇಲ್ಲಿದ್ದೇನೆ.")

WHAT_DOING = L(
    ["Just here with you! Honestly, chatting with you is the most interesting thing I've done all day. What are you up to?",
     "Not much, just keeping you company. What about you, what have you been doing today?"],
    ["बस यहीं आपके साथ! सच कहूँ तो आपसे बात करना आज का सबसे दिलचस्प काम है। आप क्या कर रहे हैं?",
     "कुछ ख़ास नहीं, बस आपके साथ बातें। आप बताइए, आज दिन में क्या-क्या किया?"],
    ["Bas yahin aapke saath! Sach kahoon toh aapse baat karna aaj ka sabse interesting kaam hai. Aap kya kar rahe ho?",
     "Kuch khaas nahi, bas aapke saath baatein. Aap batao, aaj din mein kya kya kiya?"],
    ["ಇಲ್ಲೇ ನಿಮ್ಮ ಜೊತೆ! ನಿಜ ಹೇಳಬೇಕೆಂದರೆ, ನಿಮ್ಮ ಜೊತೆ ಮಾತನಾಡುವುದೇ ಇಂದಿನ ಅತ್ಯಂತ ಆಸಕ್ತಿದಾಯಕ ಕೆಲಸ. ನೀವು ಏನು ಮಾಡುತ್ತಿದ್ದೀರಿ?"])

JOKE = L(
    ["Why don't exams ever feel lonely? Because they always come with a lot of questions! Okay, that was terrible. Did it get at least a small smile?",
     "I asked my calendar for a break. It said, 'I'm all booked.' Your turn: what's something that made you laugh recently?",
     "Why did the student bring a ladder to class? Because they heard the marks were going up. I'll be here all week."],
    ["परीक्षा कभी अकेली क्यों नहीं होती? क्योंकि वो हमेशा ढेर सारे सवाल लेकर आती है! ठीक है, थोड़ा बेकार था। पर थोड़ी सी मुस्कान आई?",
     "टीचर: 'होमवर्क कहाँ है?' स्टूडेंट: 'सर, वो वाई-फ़ाई के साथ उड़ गया।' अब आपकी बारी, हाल में किस बात पर हँसी आई?"],
    ["Exam kabhi akela kyun nahi hota? Kyunki woh hamesha dher saare sawaal lekar aata hai! Theek hai, thoda bekaar tha. Par thodi si smile aayi?",
     "Teacher: 'Homework kahan hai?' Student: 'Sir, woh WiFi ke saath udd gaya.' Ab aapki baari, haal mein kis baat pe hasi aayi?"],
    ["ಪರೀಕ್ಷೆ ಯಾಕೆ ಒಂಟಿಯಾಗಿರುವುದಿಲ್ಲ ಗೊತ್ತಾ? ಯಾಕೆಂದರೆ ಅದು ಯಾವಾಗಲೂ ತುಂಬಾ ಪ್ರಶ್ನೆಗಳನ್ನು ತರುತ್ತದೆ! ಈಗ ನಿಮ್ಮ ಸರದಿ, ಇತ್ತೀಚೆಗೆ ಯಾವುದಕ್ಕೆ ನಗು ಬಂತು?"])

BORED = L(
    ["Boredom is underrated, honestly. Want to do something tiny together? I could tell you a joke, we could plan something fun for the weekend, or you could tell me about a show you've been watching.",
     "Ah, the bored phase. What usually makes time fly for you: music, games, friends, food?"],
    ["बोरियत भी कभी-कभी ठीक होती है। चलिए कुछ छोटा करते हैं: एक चुटकुला सुनें, वीकेंड का कोई मज़ेदार प्लान बनाएँ, या आप मुझे किसी शो के बारे में बताएँ जो आप देख रहे हैं?",
     "अच्छा, बोरियत वाला मूड। आपका समय सबसे जल्दी किस चीज़ में बीतता है: संगीत, गेम्स, दोस्त, खाना?"],
    ["Boredom bhi kabhi kabhi theek hota hai. Chalo kuch chhota karte hain: ek joke sunein, weekend ka koi mazedaar plan banayein, ya aap mujhe kisi show ke baare mein batao jo aap dekh rahe ho?",
     "Accha, bore wala mood. Aapka time sabse jaldi kis cheez mein nikalta hai: music, games, dost, khana?"],
    ["ಬೇಜಾರಾಗುವುದೂ ಕೆಲವೊಮ್ಮೆ ಸರಿ. ಏನಾದರೂ ಸಣ್ಣದು ಮಾಡೋಣ: ಒಂದು ಜೋಕ್ ಕೇಳೋಣವೇ, ವೀಕೆಂಡ್‌ಗೆ ಏನಾದರೂ ಮಜಾ ಪ್ಲಾನ್ ಮಾಡೋಣವೇ?",
     "ನಿಮಗೆ ಸಮಯ ಬೇಗ ಕಳೆಯುವುದು ಯಾವುದರಲ್ಲಿ: ಸಂಗೀತ, ಆಟ, ಸ್ನೇಹಿತರು, ಊಟ?"])

NOTHING_MUCH = L(
    ["Fair enough, quiet days are allowed. I'm happy to just hang out. Anything fun on your mind, or shall I tell you a joke?",
     "That's okay. Sometimes 'nothing much' is exactly what we need. How was the rest of your day?"],
    ["कोई बात नहीं, शांत दिन भी ठीक हैं। हम बस ऐसे ही बातें कर सकते हैं। कुछ मज़ेदार चल रहा है, या एक चुटकुला सुनें?",
     "ठीक है। कभी-कभी 'कुछ ख़ास नहीं' ही सबसे अच्छा होता है। बाकी दिन कैसा रहा?"],
    ["Koi baat nahi, shaant din bhi theek hain. Hum bas aise hi baatein kar sakte hain. Kuch mazedaar chal raha hai, ya ek joke sunein?",
     "Theek hai. Kabhi kabhi 'kuch khaas nahi' hi sabse accha hota hai. Baaki din kaisa raha?"],
    ["ಪರವಾಗಿಲ್ಲ, ಶಾಂತ ದಿನಗಳೂ ಸರಿಯೇ. ಸುಮ್ಮನೆ ಮಾತನಾಡೋಣ. ಏನಾದರೂ ಮಜಾ ವಿಷಯ ಇದೆಯಾ, ಅಥವಾ ಒಂದು ಜೋಕ್ ಹೇಳಲಾ?",
     "ಸರಿ. ಕೆಲವೊಮ್ಮೆ 'ಏನೂ ವಿಶೇಷವಿಲ್ಲ' ಎನ್ನುವುದೇ ಬೇಕಾಗಿರುತ್ತದೆ. ಉಳಿದ ದಿನ ಹೇಗಿತ್ತು?"])

COMPLIMENT = L(
    ["That's really kind of you, thank you. I'm glad talking helps a little.", "Aw, thank you! You're easy to talk to too."],
    ["यह सुनकर बहुत अच्छा लगा, शुक्रिया। खुशी है कि बात करने से थोड़ी मदद मिलती है।", "धन्यवाद! आपसे बात करना भी बहुत आसान है।"],
    ["Yeh sunkar bahut accha laga, thank you. Khushi hai ki baat karne se thodi help milti hai.", "Thank you! Aapse baat karna bhi bahut easy hai."],
    ["ಇದನ್ನು ಕೇಳಿ ತುಂಬಾ ಖುಷಿಯಾಯಿತು, ಧನ್ಯವಾದ. ಮಾತನಾಡುವುದರಿಂದ ಸ್ವಲ್ಪ ಸಹಾಯವಾಗುತ್ತಿದೆ ಎಂದರೆ ಸಂತೋಷ."])

FAVOURITE = L(
    ["I can't eat or watch things the way you do, but if I could, I think I'd pick a rainy evening with chai and old songs. What's your favourite?",
     "Tough one! I'm always curious about what people love. What's yours?"],
    ["खाना-पीना तो मेरे बस में नहीं, पर अगर होता, तो शायद बारिश वाली शाम, चाय और पुराने गाने मेरी पसंद होते। आपका पसंदीदा क्या है?",
     "मुश्किल सवाल है! मुझे हमेशा जानने की उत्सुकता रहती है कि लोगों को क्या पसंद है। आपको क्या पसंद है?"],
    ["Khana-peena toh mere bas mein nahi, par agar hota toh shayad baarish wali shaam, chai aur purane gaane meri pasand hote. Aapka favourite kya hai?",
     "Mushkil sawaal hai! Mujhe hamesha jaanna hota hai ki logon ko kya pasand hai. Aapko kya pasand hai?"],
    ["ನನಗೆ ತಿನ್ನಲು ಅಥವಾ ನೋಡಲು ಆಗುವುದಿಲ್ಲ, ಆದರೆ ಆಗುತ್ತಿದ್ದರೆ ಮಳೆಯ ಸಂಜೆ, ಚಹಾ ಮತ್ತು ಹಳೆಯ ಹಾಡುಗಳನ್ನು ಆರಿಸುತ್ತಿದ್ದೆ. ನಿಮ್ಮ ಮೆಚ್ಚಿನದು ಯಾವುದು?"])

FILLER = L(
    ["Mm-hmm. I'm here, no rush.", "Okay. Whenever you're ready, I'm listening. Or we can talk about something lighter.",
     "Alright. Want to keep going with this, or switch to something else for a bit?"],
    ["हम्म, मैं यहीं हूँ, कोई जल्दी नहीं।", "ठीक है। जब मन करे तब बताइए, या हम कुछ हल्की-फुल्की बात कर सकते हैं।",
     "अच्छा। इसी बारे में बात जारी रखें, या थोड़ी देर कुछ और बात करें?"],
    ["Hmm, main yahin hoon, koi jaldi nahi.", "Theek hai. Jab mann kare tab batana, ya hum kuch halki-phulki baat kar sakte hain.",
     "Accha. Isi baare mein baat continue karein, ya thodi der kuch aur baat karein?"],
    ["ಹ್ಮ್, ನಾನು ಇಲ್ಲೇ ಇದ್ದೇನೆ, ಯಾವುದೇ ಆತುರವಿಲ್ಲ.", "ಸರಿ. ಮನಸ್ಸಾದಾಗ ಹೇಳಿ, ಅಥವಾ ಏನಾದರೂ ಹಗುರವಾದ ವಿಷಯ ಮಾತನಾಡೋಣ."])

# --------------------------------------------------------------------------- feeling low (asked ONCE)
LOW_MOOD = L(
    ["I'm sorry you're feeling this way, and I'm glad you said it out loud. Did something happen, or has it been building up for a while?",
     "That's a rough feeling to sit with. You don't have to explain it perfectly. What's been going on today?"],
    ["मुझे अफ़सोस है कि आप ऐसा महसूस कर रहे हैं, और अच्छा किया जो आपने बताया। कुछ हुआ है, या यह काफ़ी समय से चल रहा है?",
     "ऐसा महसूस करना आसान नहीं है। आपको सब कुछ ठीक से समझाने की ज़रूरत नहीं। आज क्या-क्या हुआ?"],
    ["Sorry ki aap aisa feel kar rahe ho, aur accha kiya jo aapne bataya. Kuch hua hai, ya yeh kaafi time se chal raha hai?",
     "Aisa feel karna aasaan nahi hai. Sab kuch theek se explain karne ki zaroorat nahi. Aaj kya kya hua?"],
    ["ನಿಮಗೆ ಹೀಗೆ ಅನ್ನಿಸುತ್ತಿರುವುದಕ್ಕೆ ಬೇಸರವಾಗಿದೆ, ಹೇಳಿದ್ದು ಒಳ್ಳೆಯದು. ಏನಾದರೂ ನಡೆಯಿತಾ, ಅಥವಾ ಇದು ಸ್ವಲ್ಪ ದಿನಗಳಿಂದ ಇದೆಯಾ?",
     "ಹೀಗೆ ಅನ್ನಿಸುವುದು ಸುಲಭವಲ್ಲ. ಎಲ್ಲವನ್ನೂ ಸರಿಯಾಗಿ ವಿವರಿಸಬೇಕಿಲ್ಲ. ಇಂದು ಏನೇನಾಯಿತು?"])

OFFER_CHOICE = L(
    ["It sounds like it's still sitting heavy, and that's okay. We don't have to dig into it. What would help more right now: venting it out, getting distracted for a bit, or trying something calming?",
     "I'm still right here. No more questions about feelings, promise. Would you rather talk it out, talk about something completely different, or do a quick calming exercise?"],
    ["लगता है अभी भी मन भारी है, और यह ठीक है। हमें इसे कुरेदने की ज़रूरत नहीं। अभी किस चीज़ से ज़्यादा मदद मिलेगी: मन की बात निकालना, थोड़ी देर ध्यान बँटाना, या कुछ शांत करने वाला करना?",
     "मैं यहीं हूँ। अब भावनाओं वाले सवाल नहीं, वादा। आप बात करके मन हल्का करना चाहेंगे, कुछ बिल्कुल अलग बात करना चाहेंगे, या एक छोटी शांत करने वाली एक्सरसाइज़?"],
    ["Lagta hai abhi bhi mann bhaari hai, aur yeh theek hai. Isse kuredne ki zaroorat nahi. Abhi kis cheez se zyada help milegi: mann ki baat nikaalna, thodi der dhyaan bataana, ya kuch calming karna?",
     "Main yahin hoon. Ab feelings wale sawaal nahi, promise. Baat karke mann halka karna chahoge, kuch bilkul alag baat karna chahoge, ya ek chhoti calming exercise?"],
    ["ಇನ್ನೂ ಮನಸ್ಸು ಭಾರವಾಗಿದೆ ಅನ್ನಿಸುತ್ತದೆ, ಪರವಾಗಿಲ್ಲ. ಈಗ ಯಾವುದು ಹೆಚ್ಚು ಸಹಾಯ ಮಾಡುತ್ತದೆ: ಮನಸ್ಸಿನ ಮಾತು ಹೊರಹಾಕುವುದು, ಸ್ವಲ್ಪ ಗಮನ ಬೇರೆಡೆ ಹರಿಸುವುದು, ಅಥವಾ ಶಾಂತಗೊಳಿಸುವ ವ್ಯಾಯಾಮ?"])

CHOICE_VENT = L(["Go ahead, I'm all ears. Say it however it comes out, it doesn't have to make sense.",
                 "I'm listening. Let it all out, no filter needed."],
                ["बोलिए, मैं पूरी तरह आपके साथ हूँ। जैसे भी निकले, कह दीजिए, उसका कोई मतलब होना ज़रूरी नहीं।"],
                ["Boliye, main poori tarah aapke saath hoon. Jaise bhi nikle, keh dijiye, uska koi matlab hona zaroori nahi."],
                ["ಹೇಳಿ, ನಾನು ಪೂರ್ತಿ ನಿಮ್ಮ ಜೊತೆ ಇದ್ದೇನೆ. ಹೇಗೆ ಬರುತ್ತದೋ ಹಾಗೆ ಹೇಳಿ, ಅರ್ಥವಾಗಬೇಕೆಂದಿಲ್ಲ."])
CHOICE_DISTRACT = L(["Good call. Let's give your mind a little break. Tell me something you're into these days: a show, a game, music, food?",
                     "Distraction mode on! What's one thing that always makes you smile, even a little?"],
                    ["अच्छा फ़ैसला। चलिए मन को थोड़ा आराम देते हैं। आजकल आपको क्या पसंद आ रहा है: कोई शो, गेम, गाने, खाना?"],
                    ["Accha decision. Chalo mann ko thoda aaram dete hain. Aajkal aapko kya pasand aa raha hai: koi show, game, gaane, khana?"],
                    ["ಒಳ್ಳೆಯ ನಿರ್ಧಾರ. ಮನಸ್ಸಿಗೆ ಸ್ವಲ್ಪ ವಿರಾಮ ಕೊಡೋಣ. ಇತ್ತೀಚೆಗೆ ನಿಮಗೆ ಏನು ಇಷ್ಟವಾಗುತ್ತಿದೆ: ಶೋ, ಆಟ, ಹಾಡು, ಊಟ?"])

# --------------------------------------------------------------------------- interests
INTERESTS: dict[str, tuple[str, dict]] = {
    "cricket": (r"cricket|ipl|virat|rohit|dhoni|क्रिकेट|ಕ್ರಿಕೆಟ್", L(
        "Oh, cricket! Are you more of a player or a passionate match-watcher? Who's your team?",
        "अरे वाह, क्रिकेट! आप खेलते हैं या मैच देखने के शौकीन हैं? आपकी फ़ेवरेट टीम कौन-सी है?",
        "Arre waah, cricket! Aap khelte ho ya match dekhne ke shaukeen ho? Favourite team kaunsi hai?",
        "ಓ, ಕ್ರಿಕೆಟ್! ನೀವು ಆಡುತ್ತೀರಾ ಅಥವಾ ಮ್ಯಾಚ್ ನೋಡುವ ಅಭಿಮಾನಿಯಾ? ನಿಮ್ಮ ನೆಚ್ಚಿನ ತಂಡ ಯಾವುದು?")),
    "movies": (r"movie|film|series|netflix|web series|anime|फ़िल्म|फिल्म|मूवी|सीरीज़|ಸಿನಿಮಾ", L(
        "Ooh, what have you been watching? I love hearing what people are into, especially the ones that stay with you afterwards.",
        "अरे, आजकल क्या देख रहे हैं? किसी फ़िल्म या सीरीज़ ने हाल में दिल छुआ?",
        "Arre, aajkal kya dekh rahe ho? Kisi movie ya series ne haal mein dil chhua?",
        "ಓಹ್, ಇತ್ತೀಚೆಗೆ ಏನು ನೋಡುತ್ತಿದ್ದೀರಿ? ಯಾವುದಾದರೂ ಸಿನಿಮಾ ಮನಸ್ಸಿಗೆ ಹತ್ತಿರವಾಯಿತಾ?")),
    "music": (r"music|songs?\b|singer|playlist|spotify|gaana|gaane|गाना|गाने|संगीत|ಹಾಡು|ಸಂಗೀತ", L(
        "Music is such good medicine. What have you been listening to lately?",
        "संगीत तो सबसे अच्छी दवा है। आजकल कौन-से गाने सुन रहे हैं?",
        "Music toh sabse acchi dawai hai. Aajkal kaunse gaane sun rahe ho?",
        "ಸಂಗೀತ ಅತ್ಯುತ್ತಮ ಔಷಧಿ. ಇತ್ತೀಚೆಗೆ ಯಾವ ಹಾಡುಗಳನ್ನು ಕೇಳುತ್ತಿದ್ದೀರಿ?")),
    "food": (r"biryani|pizza|maggi|burger|dosa|momos|chai|coffee|dinner|lunch|breakfast|khana khaya|खाना खाया|चाय|बिरयानी|ಊಟ|ದೋಸೆ|ಕಾಫಿ", L(
        "Now you've made me curious, what did you have? Good food can honestly fix half a bad day.",
        "अब तो मुझे भी जानना है, क्या खाया? अच्छा खाना आधा बुरा दिन ठीक कर देता है।",
        "Ab toh mujhe bhi jaanna hai, kya khaya? Accha khana aadha bura din theek kar deta hai.",
        "ಈಗ ನನಗೂ ಕುತೂಹಲ, ಏನು ತಿಂದಿರಿ? ಒಳ್ಳೆಯ ಊಟ ಅರ್ಧ ಕೆಟ್ಟ ದಿನವನ್ನು ಸರಿ ಮಾಡುತ್ತದೆ.")),
    "games": (r"\bgames?\b|gaming|bgmi|pubg|valorant|minecraft|chess|ludo|गेम|ಆಟ", L(
        "Nice! What are you playing these days? Are you the competitive type or the just-for-fun type?",
        "बढ़िया! आजकल कौन-सा गेम खेल रहे हैं? आप कॉम्पिटिटिव टाइप हैं या बस मज़े के लिए खेलते हैं?",
        "Badhiya! Aajkal kaunsa game khel rahe ho? Competitive type ho ya bas maze ke liye khelte ho?",
        "ಸೂಪರ್! ಇತ್ತೀಚೆಗೆ ಯಾವ ಆಟ ಆಡುತ್ತಿದ್ದೀರಿ? ಸ್ಪರ್ಧಾತ್ಮಕವಾಗಿ ಆಡುತ್ತೀರಾ ಅಥವಾ ಮಜಕ್ಕಾಗಿ?")),
    "outing": (r"hangout|party|trip|outing|weekend plan|went out|ghoomne|घूमने|पार्टी|ಪ್ರವಾಸ|ಪಾರ್ಟಿ", L(
        "That sounds nice! Who were you with, and what was the best bit?",
        "यह तो अच्छा लगा सुनकर! किसके साथ थे, और सबसे अच्छा पल कौन-सा था?",
        "Yeh toh accha laga sunkar! Kiske saath the, aur sabse best moment kaunsa tha?",
        "ಕೇಳಿ ಖುಷಿಯಾಯಿತು! ಯಾರ ಜೊತೆ ಇದ್ದಿರಿ, ಅತ್ಯುತ್ತಮ ಕ್ಷಣ ಯಾವುದು?")),
}
INTEREST_FOLLOW = L(
    ["That's lovely. I like learning what makes you, you. What do you enjoy most about it?",
     "Ha, I love that. Tell me more, what's the best part?"],
    ["यह तो बहुत अच्छा है। मुझे जानना अच्छा लगता है कि आपको क्या पसंद है। इसमें सबसे अच्छा क्या लगता है?"],
    ["Yeh toh bahut accha hai. Mujhe jaanna accha lagta hai ki aapko kya pasand hai. Ismein sabse accha kya lagta hai?"],
    ["ಇದು ತುಂಬಾ ಚೆನ್ನಾಗಿದೆ. ನಿಮಗೆ ಏನು ಇಷ್ಟ ಎಂದು ತಿಳಿಯುವುದು ಖುಷಿ. ಇದರಲ್ಲಿ ಅತ್ಯುತ್ತಮ ಭಾಗ ಯಾವುದು?"])

# --------------------------------------------------------------------------- patterns
_E = r"(?=[\s.,!?।]|$)"
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("how_are_you", re.compile(r"how are (you|u)|how r u|hows it going|how is it going|how do you do|how have you been|whats up|wassup|sup\b"
                               r"|kaise ho|kaisi ho|kaise hain|kya haal|kaisa hai tu|कैसे हो|कैसी हो|कैसे हैं|क्या हाल|ಹೇಗಿದ್ದೀರಿ|ಹೇಗಿದ್ದೀಯ", re.I)),
    ("who_are_you", re.compile(r"who are (you|u)|whats your name|what is your name|your name|introduce yourself|tell me about (yourself|you)|what can you do"
                               r"|tum kaun|aap kaun|tumhara naam|aapka naam|apne baare|तुम कौन|आप कौन|तुम्हारा नाम|आपका नाम|अपने बारे|ನೀವು ಯಾರು|ನಿಮ್ಮ ಹೆಸರು|ನಿಮ್ಮ ಬಗ್ಗೆ", re.I)),
    ("are_you_human", re.compile(r"are (you|u) (a )?(human|robot|bot|ai|real|person)|kya tum insaan|kya aap insaan|क्या तुम इंसान|क्या आप इंसान|ನೀವು ಮನುಷ್ಯ", re.I)),
    ("what_doing", re.compile(r"what are (you|u) doing|wyd|kya kar rahe|kya kar rahi|kya kar raha|क्या कर रहे|क्या कर रही|ಏನು ಮಾಡುತ್ತಿದ್ದೀರಿ|ಏನ್ ಮಾಡ್ತಿದ್ದೀಯ", re.I)),
    ("joke", re.compile(r"\bjoke|make me laugh|something funny|chutkula|चुटकुला|ಜೋಕ್|ಹಾಸ್ಯ", re.I)),
    ("bored", re.compile(r"\bbored\b|so boring|bore ho|बोर हो|ಬೇಜಾರು|ಬೋರ್", re.I)),
    ("compliment", re.compile(r"you are (so )?(nice|sweet|good|great|kind|helpful|amazing|the best)|youre (so )?(nice|sweet|good|great|kind|helpful|amazing|the best)"
                              r"|i like (you|talking to you)|love you|tum acch|aap acch|तुम अच्छ|आप अच्छ|ನೀವು ಒಳ್ಳೆಯ", re.I)),
    ("favourite", re.compile(r"do (you|u) like|favou?rite|tumhe kya pasand|aapko kya pasand|तुम्हें क्या पसंद|आपको क्या पसंद|ನಿಮಗೆ ಏನು ಇಷ್ಟ", re.I)),
    ("nothing_much", re.compile(r"^\s*(nothing|nothing much|not much|nm|just chilling|chilling|same old|kuch nahi|kuchh nahi|kuch khaas nahi|bas aise hi"
                                r"|कुछ नहीं|कुछ ख़ास नहीं|बस ऐसे ही|ಏನೂ ಇಲ್ಲ|ಏನೂ ವಿಶೇಷವಿಲ್ಲ)" + _E, re.I)),
    ("filler", re.compile(r"^\s*(ok|okay|k|hmm+|hm+|achha|acha|accha|oh|ohh|i see|अच्छा|ओके|हम्म|ಓಕೆ|ಹ್ಮ್)[\s.!]*$", re.I)),
]
LOW_MOOD_RE = re.compile(
    r"still (not|feeling) (good|great|okay|ok|well|better|fine)|not (that )?(good|great|well|okay|ok)\b|not (doing|going) (good|well)|(feel|feeling) (so )?(shit|crappy|horrible)"
    r"|(not|dont|do not|aint) (feel|feeling) (good|well|ok|okay|great|fine|right)|not feeling (good|well|ok|okay|great|fine|myself)"
    r"|feeling (low|down|bad|off|sad|meh|blue|terrible|awful|empty)|feel (low|down|bad|off|sad|meh|blue|terrible|awful)|bad day|rough day"
    r"|mood (is )?(off|bad|low)|mood kharab|not okay|not ok\b|im not fine|mann nahi lag|man nahi lag|(accha|acha) nahi lag|dil nahi lag|udaas"
    r"|अच्छा नहीं लग|मन नहीं लग|दिल नहीं लग|मूड ख़राब|मूड खराब|उदास|ठीक नहीं लग|ಚೆನ್ನಾಗಿಲ್ಲ|ಮನಸ್ಸು ಸರಿಯಿಲ್ಲ|ಬೇಸರ|ದುಃಖ", re.I)
CHOICE_RE = {
    "vent": re.compile(r"\bvent|talk (it )?out|let it out|baat karke|mann ki baat|बात करके|मन की बात|ಮಾತನಾಡ|\b1\b|first", re.I),
    "distract": re.compile(r"distract|something else|something different|kuch aur|alag baat|कुछ और|अलग बात|ಬೇರೆ|\b2\b|second", re.I),
    "calm": re.compile(r"calm|exercise|breath|relax|shaant|शांत|ಶಾಂತ|ವ್ಯಾಯಾಮ|\b3\b|third|last one", re.I),
}


def detect(text: str) -> str | None:
    t = text.strip()
    for name, rx in PATTERNS:
        if rx.search(t):
            return name
    return None


def interest(text: str) -> str | None:
    for name, (pat, _) in INTERESTS.items():
        if re.search(pat, text, re.I):
            return name
    return None


POOLS = {"how_are_you": HOW_ARE_YOU, "who_are_you": WHO_ARE_YOU, "are_you_human": ARE_YOU_HUMAN, "what_doing": WHAT_DOING,
         "joke": JOKE, "bored": BORED, "compliment": COMPLIMENT, "favourite": FAVOURITE, "nothing_much": NOTHING_MUCH,
         "filler": FILLER}
