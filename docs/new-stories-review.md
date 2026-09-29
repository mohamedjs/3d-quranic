# قصص الأنبياء والصحابة — ورقة المراجعة

هذه الورقة للمراجع (شيخ/معلم) قبل الإصدار. القصص تسع، في فئتين جديدتين: **قصص الأنبياء** (أولو العزم الخمسة) و**قصص الصحابة** (الخلفاء الأربعة). تُروى على لسان شخصيات القرية المعروفة (الجدّ سالم، الجدّة زينب، الجدّة آمنة، العمّ حمدان) والطفل يسأل. البيانات: `public/data/encounters.json` (الحقول `category` و`order`، ومصفوفة `categories`).

- نصوص الآيات وتلاوتها لا تُخزَّن في اللعبة؛ تُجلب من Quran.com وقت التشغيل. الاقتباسات القرآنية القصيرة داخل الحوار (بين «») تحتاج مطابقة.
- لا يُعرض أيّ نبيّ ولا صحابيّ ولا مريم عليها السلام؛ الصور أماكن وأشياء وحيوانات فقط.
- المصادر: القرآن الكريم وتفسير ابن كثير والميسّر؛ والصحيحان حيث وُجدا؛ وما سواهما مذكور بدرجته. ما لا يثبت (كالعنكبوت والحمام في الغار، وقصة عمر وقِدر الحجارة) لم يُستعمل.
- عمود «النوع»: «سطر» = كلام الراوي، «سؤال» = سؤال يطرحه الراوي، «الطفل» = ما يختاره الطفل (يمضي تلقائيًا بالخيار الأول)، «ردّ» = ردّ على الطفل، «اختبار» = سؤال له جواب صحيح (✓). 🖼 = مفتاح الصورة.
- كل قصة تمنح 50 نقطة. القصة الأولى في كل فئة لا تحتاج قصة سابقة.

- ترتيب الفتح (قصص الأنبياء): نوح عليه السلام والسفينة ← إبراهيم عليه السلام: النارُ الباردة ← موسى عليه السلام: الطفل في النهر ← عيسى عليه السلام: الكلامُ في المهد ← محمد ﷺ: الصادق الأمين
- ترتيب الفتح (قصص الصحابة): أبو بكر الصدّيق: صاحبُ الغار ← عمر بن الخطّاب: الأمير الرحيم ← عثمان بن عفّان: بئرُ رُومة ← عليّ بن أبي طالب: ليلةُ الهجرة والأمانات

---

# قصص الأنبياء — Stories of the Prophets

## 1) نوح عليه السلام والسفينة — Nuh (Noah) and the Ark

- **المعرّف:** `nuh-and-the-ark` · **الفئة/الترتيب:** prophets / 1 · **يُفتح بعد:** — (أول الفئة) · **المنطقة:** `fields`
- **الشخصيات والمواضع:** الجدّ سالم (10.0, 62.0) facing 3.1416 · العمّ حمدان (7.5, 62.8) facing 2.5
- **الآيات المتلوّة:** 11:40–11:41 — https://quran.com/11/40
- **توجيه الراوي:** روح للجدّ سالم والعمّ حمدان على شطّ النهر، شمال الغيطان جنب الكوبري. — Go to Grandpa Salim and Uncle Hamdan on the riverbank, north of the fields near the bridge.
- **التحية:** أهلًا يا بُنيّ! انظر إلى النهر ما أوسعه! تعالَ، نحكي لك عن سفينةٍ عظيمة. · **بعد الانتهاء:** اصبر على فعل الخير، ولا تهتمّ بمن يسخر منك.
- **المصادر (تظهر في اللعبة):**
  - Qur'an 11:25–48 (https://quran.com/11/25)
  - Qur'an 71:1–28 (https://quran.com/71/1)
  - Qur'an 29:14 (https://quran.com/29/14)
  - Qur'an 54:11–14 (https://quran.com/54/11)
  - صحيح البخاري 4476 — حديث الشفاعة: «ائتوا نوحًا فإنه أول رسول بعثه الله إلى أهل الأرض» (https://sunnah.com/bukhari:4476)
  - Tafsir Ibn Kathir — Surat Hud
  - Tafsir al-Muyassar — Surat Hud

**نقاط تحتاج نظر المراجع:**

- لم يُذكر ابن نوح الذي أبى الركوب وغرق (11:42–43) مراعاةً لصغار السن — هل يُضاف بلطف؟
- الغرق مذكور بجملة واحدة لطيفة: «وأمّا الذين أصرّوا على العناد فلم ينجوا».
- «تحت رعاية الله وبتعليمه» = معنى «بأعيننا ووحينا» (11:37).
- «الألواح والمسامير» = «ذات ألواح ودُسُر» (54:13).
- ملاحظة البيانات (`_note`): Qur'an-only retelling. Left out for young children: Nuh's son who refused and drowned (11:42–43), and any drowning details; only 'those who stubbornly refused were not saved'. No numbers of believers, ark size or animal lists (not in the Qur'an). Verses 11:40–41 are played.

**الحوار كاملًا:**

| # | المتكلّم | النص | English | النوع |
|---|---|---|---|---|
| 1 | الجدّ سالم | أهلًا يا بُنيّ! نحن الفلاحين نعرف قيمة الماء، به تحيا الأرض. والماء أيضًا جزءٌ من قصةٍ عظيمة في القرآن: قصة نوح عليه السلام. | Hello, my son! We farmers know how precious water is — it brings the land to life. And water is part of a great story in the Quran: the story of Nuh, peace be upon him. | سطر |
| 2 | العمّ حمدان | هل تعرف مَن هو نوح عليه السلام؟ | Do you know who Nuh, peace be upon him, was? | سؤال |
| 3 | الطفل | نبيٌّ صنع سفينة؟ | A prophet who built a ship? | الطفل |
| 4 | العمّ حمدان | ↳ أحسنت! هو أوّل رسولٍ أرسله الله إلى أهل الأرض، ومن أولي العزم من الرسل، وصنع سفينةً بأمر الله. | Well done! He was the first messenger Allah sent to the people of the earth, one of the five greatest messengers — and he built a ship by Allah’s command. | ردّ |
| 5 | الطفل | لا، احكيا لي! | No — tell me! | الطفل |
| 6 | الجدّ سالم | ↳ من عينيّ! هو أوّل رسولٍ أرسله الله إلى أهل الأرض، ومن أولي العزم من الرسل. اسمع يا بُنيّ. | With all my heart! He was the first messenger Allah sent to the people of the earth, one of the five greatest messengers. Listen, my son. | ردّ |
| 7 | الطفل | ولماذا أرسله الله؟ | Why did Allah send him? | الطفل |
| 8 | الجدّ سالم | ↳ كان قومُه يعبدون أصنامًا لا تنفع ولا تضرّ. فأرسل الله إليهم نوحًا ليقول لهم: اعبدوا الله وحده. | His people worshipped idols that could neither help nor harm. So Allah sent Nuh to tell them: worship Allah alone. | ردّ |
| 9 | العمّ حمدان | ↳ ودعاهم نوحٌ ليلًا ونهارًا، سرًّا وجهرًا، وصبر عليهم زمنًا طويلًا جدًّا: ألفَ سنةٍ إلا خمسين عامًا! | Nuh called them night and day, quietly and openly, and was patient with them for a very long time — a thousand years less fifty! | ردّ |
| 10 | الطفل | كلّ هذه السنين؟! وهل آمنوا به؟ | All those years?! Did they believe him? | الطفل |
| 11 | الجدّ سالم | ↳ آمن معه قليلٌ من الناس فقط، وأكثرُهم رفضوا وسخروا منه. ومع ذلك ظلّ يدعوهم برفقٍ وصبر. | Only a few people believed with him; most refused and made fun of him. Still, he kept calling them gently and patiently. | ردّ |
| 12 | الطفل | وماذا أمره الله أن يفعل؟ | What did Allah tell him to do? | الطفل |
| 13 | العمّ حمدان | ↳ أوحى الله إلى نوح أنّه لن يؤمن من قومه إلا مَن قد آمن، وأمره أن يصنع سفينةً، تحت رعاية الله وبتعليمه. | Allah revealed to Nuh that no more of his people would believe except those who already had, and told him to build a ship — under Allah’s care and by His teaching. | ردّ 🖼 `ark_build` |
| 14 | الجدّ سالم | ↳ فبدأ نوحٌ يصنع السفينة من الألواح والمسامير. وكلّما مرّ عليه جماعةٌ من قومه سخروا منه، وهو يُكمل عمله. | So Nuh began building the ship from planks and nails. Every time a group of his people passed by they laughed at him — and he kept on working. | ردّ 🖼 `ark_build` |
| 15 | العمّ حمدان | ماذا فعل نوحٌ حين سخر منه قومه وهو يصنع السفينة؟ | What did Nuh do when his people laughed at him while he built the ship? | اختبار |
| 16 | الطفل | ✓ صبر وأكمل عمله كما أمره الله | He was patient and finished the work Allah told him to do | خيار |
| 17 | الطفل | ✗ ترك السفينة وغضب | He left the ship and got angry | خيار |
| 18 | الطفل | ✗ نام ولم يعمل | He went to sleep and stopped working | خيار |
| 19 | العمّ حمدان | تلميح: تذكّر: كان نوحٌ صبورًا جدًّا… | Remember: Nuh was very patient… | تلميح |
| 20 | العمّ حمدان | ثناء: أحسنت! أكمل السفينة وتوكّل على الله. | Well done! He finished the ship and trusted in Allah. | ثناء |
| 21 | الطفل | وماذا ركب معه في السفينة؟ | Who went with him on the ship? | الطفل |
| 22 | الجدّ سالم | ↳ لمّا جاء أمرُ الله، أمره أن يحمل فيها من كلّ نوعٍ من الحيوانات زوجين اثنين — ذكرًا وأنثى — وأهلَه، ومَن آمن معه. | When Allah’s command came, He told him to take on board a pair of every kind of animal — a male and a female — and his family, and those who believed with him. | ردّ 🖼 `ark_build` |
| 23 | العمّ حمدان | ↳ وقال لهم نوح: «اركبوا فيها، بسم الله مجراها ومُرساها» — يعني: باسم الله تسير السفينة، وباسم الله تقف. | And Nuh said: “Board it — in the name of Allah it sails and in the name of Allah it anchors.” Meaning: with Allah’s name the ship moves, and with Allah’s name it stops. | ردّ 🖼 `ark_sea` |
| 24 | الطفل | وماذا حدث بعد ذلك؟ | What happened next? | الطفل |
| 25 | الجدّ سالم | ↳ نزل المطرُ من السماء بغزارة، وتفجّرت الأرضُ عيونًا، فجرت السفينةُ بهم في موجٍ كالجبال، والله يحفظ مَن فيها. | Rain poured down from the sky and springs burst out of the earth, and the ship sailed with them through waves like mountains — with Allah protecting everyone on board. | ردّ 🖼 `ark_sea` |
| 26 | العمّ حمدان | ↳ فأنجى الله نوحًا والمؤمنين معه، وأمّا الذين أصرّوا على العناد فلم ينجوا. | So Allah saved Nuh and the believers with him; those who stubbornly refused were not saved. | ردّ 🖼 `ark_sea` |
| 27 | الطفل | وأين وقفت السفينة؟ | Where did the ship stop? | الطفل |
| 28 | العمّ حمدان | ↳ أمر اللهُ الأرضَ أن تبلع ماءها، والسماءَ أن تُمسك مطرها، فنزل الماء، ورست السفينة على جبلٍ اسمه «الجوديّ». | Allah commanded the earth to swallow its water and the sky to hold back its rain. The water went down, and the ship came to rest on a mountain called al-Judi. | ردّ 🖼 `ark_judi` |
| 29 | الجدّ سالم | ↳ ونزل نوحٌ ومَن معه بسلامٍ وبركاتٍ من الله، وبدأت الحياة من جديد. | Nuh and those with him came down with peace and blessings from Allah, and life began again. | ردّ 🖼 `ark_judi` |
| 30 | الجدّ سالم | تعالَ نسمع الآيتين اللتين فيهما ركوب السفينة، بصوت الشيخ. | Come, let's hear the two verses about boarding the ship, in the sheikh's voice. | سطر |
| 31 | — | [تلاوة 11:40–11:41] |  | آيات |
| 32 | الجدّ سالم | فماذا نتعلّم من قصة نوح عليه السلام؟ | So what do we learn from the story of Nuh? | اختبار |
| 33 | الطفل | ✓ أن نصبر على فعل الخير ونطيع الله، والله ينجّي المؤمنين | To keep doing good patiently and obey Allah — Allah saves the believers | خيار |
| 34 | الطفل | ✗ أن نترك الخير إذا سخر منّا أحد | To stop doing good if someone laughs at us | خيار |
| 35 | الطفل | ✗ أنّ السفن لا تغرق أبدًا | That ships never sink | خيار |
| 36 | الجدّ سالم | تلميح: تذكّر: هل ترك نوحٌ السفينة لمّا سخروا منه؟ | Remember: did Nuh stop building when they laughed at him? | تلميح |
| 37 | الجدّ سالم | ثناء: ممتاز! وتذكّر أن تقول «بسم الله» حين تبدأ أيّ عمل. | Excellent! And remember to say “Bismillah” whenever you begin something. | ثناء |
| 38 | الطفل | سأقول «بسم الله»، وأصبر على الخير مثل نوح عليه السلام! | I'll say “Bismillah” and keep doing good patiently, like Nuh, peace be upon him! | سطر |
| 39 | — | [مكافأة 50 نقطة] تعلّمت قصة نوح عليه السلام والسفينة. | You learned the story of Nuh, peace be upon him, and the ark. | مكافأة |

## 2) إبراهيم عليه السلام: النارُ الباردة — Ibrahim (Abraham): The Fire Made Cool

- **المعرّف:** `ibrahim-and-the-fire` · **الفئة/الترتيب:** prophets / 2 · **يُفتح بعد:** `nuh-and-the-ark` · **المنطقة:** `desert`
- **الشخصيات والمواضع:** العمّ حمدان (141.0, -50.0) facing -0.6 · الجدّ سالم (143.0, -51.2) facing -0.82
- **الآيات المتلوّة:** 21:69–21:70 — https://quran.com/21/69
- **توجيه الراوي:** روح للغيطان الشرقية على طريق الدار القديمة، العمّ حمدان والجدّ سالم مستنيينك. — Go to the eastern fields on the road to the Old Homestead — Uncle Hamdan and Grandpa Salim are waiting for you.
- **التحية:** أهلًا يا صغيري! هل تعرف قصة الفتى الذي لم يخَف إلا من الله؟ · **بعد الانتهاء:** فكّر بعقلك، واعبد الله وحده، وتوكّل عليه. · **رسالة القفل:** أهلًا يا صغيري! اسمع أولًا قصة «نوح والسفينة» عند شاطئ النهر، ثم تعالَ إلينا.
- **المصادر (تظهر في اللعبة):**
  - Qur'an 21:51–71 (https://quran.com/21/51)
  - Qur'an 37:83–98 (https://quran.com/37/83)
  - صحيح البخاري 4563 — ابن عباس: «حسبنا الله ونعم الوكيل» قالها إبراهيم عليه السلام حين أُلقي في النار (https://sunnah.com/bukhari:4563)
  - Tafsir Ibn Kathir — Surat al-Anbiya
  - Tafsir al-Muyassar — Surat al-Anbiya

**نقاط تحتاج نظر المراجع:**

- «عيد لهم خارج المدينة» من التفسير (37:88–90، ابن كثير).
- قوله «بل فعله كبيرهم هذا» عُرض — كما في التفسير — وسيلةً ليفكّروا؛ يرجى مراجعة الصياغة.
- النار مذكورة بلا تفاصيل إحراق، ولا تُتلى 21:68 «حرّقوه»؛ تُتلى 21:69–70.
- «حسبنا الله ونعم الوكيل» من البخاري 4563 (ابن عباس).
- ملاحظة البيانات (`_note`): Qur'an retelling plus Bukhari 4563. 'A festival outside the town' is from tafsir of 37:88–90 (Ibn Kathir). His words «بل فعله كبيرهم هذا فاسألوهم إن كانوا ينطقون» are presented, as in tafsir, as a way to make them think — please review. The fire is told gently (no burning details); 21:68 «حرّقوه» is not played — only 21:69–70.

**الحوار كاملًا:**

| # | المتكلّم | النص | English | النوع |
|---|---|---|---|---|
| 1 | العمّ حمدان | أهلًا يا صغيري! قصتنا اليوم عن نبيّ الله إبراهيم عليه السلام، خليل الرحمن. كان فتًى ذكيًّا، يفكّر بعقله، ويحبّ الله. | Hello, little one! Today's story is about Allah's prophet Ibrahim, peace be upon him, the friend of the Most Merciful. He was a clever young man who thought with his mind and loved Allah. | سطر |
| 2 | الجدّ سالم | هل تعرف ماذا كان يعبد قومُه؟ | Do you know what his people worshipped? | سؤال |
| 3 | الطفل | أصنامًا؟ | Idols? | الطفل |
| 4 | الجدّ سالم | ↳ صحيح يا بُنيّ. كانوا ينحتون تماثيل بأيديهم، ثم يعبدونها! | Right, my son. They carved statues with their own hands — and then worshipped them! | ردّ |
| 5 | الطفل | لا، ماذا؟ | No — what? | الطفل |
| 6 | الجدّ سالم | ↳ كانوا ينحتون تماثيل بأيديهم، ثم يعبدونها! | They carved statues with their own hands — and then worshipped them! | ردّ |
| 7 | الطفل | وماذا قال لهم إبراهيم؟ | What did Ibrahim say to them? | الطفل |
| 8 | العمّ حمدان | ↳ سألهم إبراهيم: «ما هذه التماثيلُ التي أنتم لها عاكفون؟» فقالوا: وجدنا آباءنا لها عابدين. | Ibrahim asked them: “What are these statues you are so devoted to?” They said: “We found our fathers worshipping them.” | ردّ |
| 9 | الجدّ سالم | ↳ فقال لهم: ربُّكم هو ربُّ السماوات والأرض، الذي خلقهنّ، وهو وحده الذي يستحقّ العبادة. | He told them: your Lord is the Lord of the heavens and the earth, who created them — He alone deserves to be worshipped. | ردّ |
| 10 | الطفل | وهل سمعوا كلامه؟ | Did they listen? | الطفل |
| 11 | العمّ حمدان | ↳ لا. فأراد إبراهيم أن يُريهم بعيونهم أنّ الأصنام لا تنفع شيئًا. فلمّا خرج قومُه من المدينة إلى عيدٍ لهم، ذهب إلى الأصنام… | No. So Ibrahim wanted to show them with their own eyes that idols are no use at all. When his people went out of town for a festival, he went to the idols… | ردّ |
| 12 | العمّ حمدان | ↳ فكسّرها قطعًا، إلا الصنمَ الكبير تركه، لعلّهم يرجعون إليه ويسألونه. | …and broke them to pieces — all except the biggest one, which he left, so that they might go back to it and ask. | ردّ 🖼 `idols_broken` |
| 13 | الطفل | ولماذا ترك الصنم الكبير؟ | Why did he leave the big idol? | الطفل |
| 14 | الجدّ سالم | ↳ لمّا رجعوا قالوا: مَن فعل هذا بآلهتنا؟ فجاؤوا بإبراهيم وسألوه. فقال: «بل فعله كبيرُهم هذا، فاسألوهم إن كانوا ينطقون». | When they came back they said: “Who did this to our gods?” They brought Ibrahim and asked him. He said: “Rather, this biggest one of them did it — so ask them, if they can speak!” | ردّ 🖼 `idols_broken` |
| 15 | العمّ حمدان | ↳ أراد أن يجعلهم يفكّرون: كيف تعبدون شيئًا لا يتكلّم، ولا يدافع عن نفسه؟ فعرفوا في أنفسهم أنّ الأصنام لا تنطق. | He wanted them to think: how can you worship something that can't speak, and can't even protect itself? And deep down they knew the idols could not speak. | ردّ 🖼 `idols_broken` |
| 16 | الطفل | وهل آمنوا بعد ذلك؟ | Did they believe after that? | الطفل |
| 17 | الجدّ سالم | ↳ للأسف لا. غضبوا وعاندوا، وقرّروا أن يُلقوا إبراهيم في نارٍ عظيمة. | Sadly, no. They got angry and stubborn, and decided to throw Ibrahim into a huge fire. | ردّ |
| 18 | العمّ حمدان | ↳ لكنّ إبراهيم لم يخَف، وقال كلمةً عظيمة: «حسبُنا اللهُ ونِعمَ الوكيل» — يعني: الله يكفيني، وهو خيرُ مَن أعتمد عليه. | But Ibrahim was not afraid. He said great words: “Allah is enough for us, and He is the best to rely on.” | ردّ |
| 19 | الطفل | وماذا فعلت النار؟ | And what did the fire do? | الطفل |
| 20 | العمّ حمدان | ↳ هنا المعجزة! قال الله: «يا نارُ كوني بَردًا وسلامًا على إبراهيم». فصارت النار باردةً لطيفة، لم تؤذه أبدًا! | Here is the miracle! Allah said: “O fire, be cool and safe for Ibrahim!” And the fire became cool and gentle — it did not hurt him at all! | ردّ 🖼 `cool_fire` |
| 21 | الجدّ سالم | ↳ فالنار لا تحرق إلا بإذن الله، لأنّ الله هو الذي خلقها. فخرج إبراهيم منها سالمًا، ونجّاه الله. | Fire only burns by Allah’s permission, because Allah created it. Ibrahim came out safe and sound — Allah saved him. | ردّ 🖼 `cool_fire` |
| 22 | الجدّ سالم | ماذا قال الله للنار؟ | What did Allah say to the fire? | اختبار |
| 23 | الطفل | ✓ كوني بردًا وسلامًا على إبراهيم | Be cool and safe for Ibrahim | خيار |
| 24 | الطفل | ✗ اشتعلي أكثر | Burn even more | خيار |
| 25 | الطفل | ✗ انطفئي غدًا | Go out tomorrow | خيار |
| 26 | الجدّ سالم | تلميح: كانت النار باردةً ولطيفة… | The fire became cool and gentle… | تلميح |
| 27 | الجدّ سالم | ثناء: أحسنت! الله على كلّ شيءٍ قدير. | Well done! Allah has power over all things. | ثناء |
| 28 | العمّ حمدان | تعالَ نسمع الآيتين بصوت الشيخ. | Come, let's hear the two verses in the sheikh's voice. | سطر |
| 29 | — | [تلاوة 21:69–21:70] |  | آيات |
| 30 | العمّ حمدان | فماذا نتعلّم من قصة إبراهيم عليه السلام؟ | So what do we learn from the story of Ibrahim? | اختبار |
| 31 | الطفل | ✓ أن نفكّر بعقولنا ونعبد الله وحده، ونتوكّل عليه | To think with our minds, worship Allah alone and trust in Him | خيار |
| 32 | الطفل | ✗ أن نفعل ما يفعله الناس دون تفكير | To do whatever everyone does without thinking | خيار |
| 33 | الطفل | ✗ أن نخاف من كلّ شيء | To be afraid of everything | خيار |
| 34 | العمّ حمدان | تلميح: تذكّر: قال إبراهيم «حسبنا الله ونعم الوكيل»… | Remember what Ibrahim said: “Allah is enough for us…” | تلميح |
| 35 | العمّ حمدان | ثناء: ممتاز! وإذا خفتَ من شيء فقل: حسبنا الله ونعم الوكيل. | Excellent! And whenever you are afraid, say: “Allah is enough for us, and He is the best to rely on.” | ثناء |
| 36 | الطفل | حسبُنا اللهُ ونعم الوكيل! | Allah is enough for us, and He is the best to rely on! | سطر |
| 37 | — | [مكافأة 50 نقطة] تعلّمت قصة إبراهيم عليه السلام والنار الباردة. | You learned the story of Ibrahim, peace be upon him, and the fire made cool. | مكافأة |

## 3) موسى عليه السلام: الطفل في النهر — Musa (Moses): The Baby on the River

- **المعرّف:** `musa-on-the-river` · **الفئة/الترتيب:** prophets / 3 · **يُفتح بعد:** `ibrahim-and-the-fire` · **المنطقة:** `fields`
- **الشخصيات والمواضع:** الجدّة آمنة (-41.8, 32.0) facing 1.5708
- **دعائم:** basket (-41.9, 33.4)
- **الآيات المتلوّة:** 28:7–28:7 — https://quran.com/28/7
- **توجيه الراوي:** زور الجدّة آمنة جنب الترعة الغربية وسط الغيطان، شمال غرب القرية. — Visit Grandma Amina by the western canal among the fields, north-west of the village.
- **التحية:** أهلًا يا حبيبي! انظر إلى ماء الترعة يجري… هذا الماء يأتي من النيل. تعالَ أحكِ لك عن طفلٍ حمله النيل. · **بعد الانتهاء:** وعدُ الله حقّ، فلا تخف ولا تحزن. · **رسالة القفل:** أهلًا يا حبيبي! اسمع أولًا قصة «إبراهيم والنار الباردة» في الغيطان الشرقية، ثم تعالَ إليّ.
- **المصادر (تظهر في اللعبة):**
  - Qur'an 28:4–13 (https://quran.com/28/4)
  - Qur'an 20:37–40 (https://quran.com/20/37)
  - Tafsir Ibn Kathir — Surat al-Qasas (اليمّ: نهر النيل)
  - Tafsir al-Muyassar — Surat al-Qasas

**نقاط تحتاج نظر المراجع:**

- قتل فرعون للأولاد (28:4) مذكور بلطف: «يأمر جنوده أن يؤذوا أولادهم الصغار».
- قول امرأة فرعون «لا تقتلوه» (28:9) صيغ: «اتركوه لنا».
- «في مصر، على شاطئ النيل»: اليمّ هو النيل كما في ابن كثير.
- «صندوق» = التابوت (20:39)؛ الصورة المقترحة صندوق/سلّة صغيرة من البردي.
- ملاحظة البيانات (`_note`): Qur'an-only retelling. Pharaoh's killing of baby boys (28:4) is told gently as 'ordered his soldiers to harm their little boys'. Pharaoh's wife's «لا تقتلوه» (28:9) is paraphrased as 'leave him with us'. 'In Egypt, on the Nile' follows tafsir (Ibn Kathir: اليم = النيل). Only 28:7 (the promise to Musa's mother) is played.

**الحوار كاملًا:**

| # | المتكلّم | النص | English | النوع |
|---|---|---|---|---|
| 1 | الجدّة آمنة | أهلًا يا حبيبي! منذ زمنٍ بعيدٍ جدًّا، هنا في مصر، على شاطئ النيل، وُلد طفلٌ صغير صار نبيًّا عظيمًا: موسى عليه السلام. | Hello, my darling! A very long time ago, here in Egypt, on the banks of the Nile, a little baby was born who became a great prophet: Musa, peace be upon him. | سطر |
| 2 | الجدّة آمنة | هل تعرف قصة موسى وهو رضيع؟ | Do you know the story of Musa as a baby? | سؤال |
| 3 | الطفل | لا يا جدّتي، احكي لي! | No, Grandma — tell me! | الطفل |
| 4 | الجدّة آمنة | ↳ اسمع يا حبيبي. إنها قصةٌ عن أمٍّ تحبّ ابنها، وعن وعدٍ من الله. | Listen, my darling. It's a story about a mother who loved her son, and a promise from Allah. | ردّ |
| 5 | الطفل | سمعتُ عن صندوقٍ في النهر… | I heard about a box on the river… | الطفل |
| 6 | الجدّة آمنة | ↳ صحيح! اسمع القصة من أوّلها. | That's right! Listen to the story from the beginning. | ردّ |
| 7 | الطفل | ولماذا كانت أمّ موسى خائفة؟ | Why was Musa's mother afraid? | الطفل |
| 8 | الجدّة آمنة | ↳ كان في مصر ملكٌ ظالمٌ متكبّر اسمه فرعون. كان يظلم بني إسرائيل، ويأمر جنوده أن يؤذوا أولادهم الصغار. | Egypt had a cruel, proud king called Pharaoh. He was unjust to the Children of Israel and ordered his soldiers to harm their little boys. | ردّ 🖼 `palace_nile` |
| 9 | الطفل | وماذا فعلت أمّ موسى؟ | What did Musa's mother do? | الطفل |
| 10 | الجدّة آمنة | ↳ ألهمها الله — أي وضع في قلبها — أن تُرضعه، فإذا خافت عليه تضعه في صندوق، وتُلقيه في اليمّ — أي في النهر. | Allah inspired her — He put it in her heart — to nurse him, and when she feared for him, to put him in a box and place it on the river. | ردّ 🖼 `nile_basket` |
| 11 | الجدّة آمنة | ↳ ووعدها الله وعدًا جميلًا: «ولا تخافي ولا تحزني، إنّا رادّوه إليكِ، وجاعلوه من المرسلين». | And Allah gave her a beautiful promise: “Do not fear and do not grieve — We will return him to you and make him one of the messengers.” | ردّ 🖼 `nile_basket` |
| 12 | الطفل | وهل وضعته في النهر فعلًا؟ | Did she really put him on the river? | الطفل |
| 13 | الجدّة آمنة | ↳ نعم، وضعته في الصندوق وتركته يجري على ماء النيل، والله يحرسه. وقالت لأخته: «قُصّيه» — أي امشي وراءه وانظري أين يذهب. | Yes. She put him in the box and let it float on the Nile, with Allah watching over him. And she told his sister: “Follow him” — walk after him and see where he goes. | ردّ 🖼 `nile_basket` |
| 14 | الجدّة آمنة | ↳ فمشت أختُه على الشاطئ تراقبه من بعيد، ولم يشعر بها أحد. | So his sister walked along the bank, watching from far away, and no one noticed her. | ردّ 🖼 `nile_basket` |
| 15 | الطفل | وإلى أين أخذه الماء؟ | Where did the water take him? | الطفل |
| 16 | الجدّة آمنة | ↳ أخذه الماء إلى قصر فرعون نفسه! فالتقطه أهلُ فرعون. ولكنّ الله ألقى عليه محبّةً منه، فكلّ مَن رآه أحبّه. | The water took him right to Pharaoh's own palace! Pharaoh's household picked him up. But Allah had placed love for him in people's hearts — everyone who saw him loved him. | ردّ 🖼 `palace_nile` |
| 17 | الجدّة آمنة | ↳ فقالت امرأةُ فرعون: هذا الطفل فرحةٌ لي ولك، اتركوه لنا، عسى أن ينفعنا أو نتّخذه ولدًا. | Pharaoh's wife said: “This child is a joy for me and for you. Leave him with us — perhaps he will benefit us, or we will adopt him as a son.” | ردّ 🖼 `palace_nile` |
| 18 | الطفل | ومَن أرضعه في القصر؟ | Who fed him in the palace? | الطفل |
| 19 | الجدّة آمنة | ↳ هنا العجيبة! جعله الله يرفض أن يرضع من أيّ امرأة، فاحتار أهلُ القصر. | Here's the wonder! Allah made him refuse to nurse from any woman, and the palace people didn't know what to do. | ردّ |
| 20 | الجدّة آمنة | ↳ فجاءت أخته وقالت: هل أدلّكم على أهل بيتٍ يكفلونه لكم، ويعتنون به بإخلاص؟ | Then his sister came and said: “Shall I show you a family who will look after him for you, and care for him sincerely?” | ردّ |
| 21 | الطفل | ورجع إلى أمّه؟! | And he went back to his mother?! | الطفل |
| 22 | الجدّة آمنة | ↳ نعم! ردّه الله إلى أمّه لترضعه، فقرّت عينُها ولم تحزن، وعلمت أنّ وعدَ الله حقّ. | Yes! Allah returned him to his mother so she could nurse him. She was comforted, her sadness gone, and she knew Allah's promise is true. | ردّ |
| 23 | الجدّة آمنة | ↳ ثم كبر موسى، وجعله الله نبيًّا من أولي العزم من الرسل، كما وعد. | Then Musa grew up, and Allah made him one of the five greatest messengers — just as He had promised. | ردّ |
| 24 | الجدّة آمنة | مَن حفظ موسى وهو صغيرٌ في النهر؟ | Who protected baby Musa on the river? | اختبار |
| 25 | الطفل | ✓ الله سبحانه وتعالى | Allah, the Most High | خيار |
| 26 | الطفل | ✗ فرعون | Pharaoh | خيار |
| 27 | الطفل | ✗ الصندوق وحده | Just the box | خيار |
| 28 | الجدّة آمنة | تلميح: تذكّر وعدَ الله لأمّه: «إنّا رادّوه إليكِ»… | Remember Allah's promise to his mother: “We will return him to you”… | تلميح |
| 29 | الجدّة آمنة | ثناء: أحسنت! الله حفظه، وردّه إلى أمّه كما وعد. | Well done! Allah protected him and returned him to his mother, just as He promised. | ثناء |
| 30 | الجدّة آمنة | تعالَ نسمع الآية التي فيها وعدُ الله لأمّ موسى، بصوت الشيخ. | Come, let's hear the verse with Allah's promise to Musa's mother, in the sheikh's voice. | سطر |
| 31 | — | [تلاوة 28:7–28:7] |  | آيات |
| 32 | الجدّة آمنة | فماذا نتعلّم من هذه القصة؟ | So what do we learn from this story? | اختبار |
| 33 | الطفل | ✓ أنّ وعدَ الله حقّ، وأنّ الله يحفظ مَن يتوكّل عليه | Allah's promise is true, and Allah protects those who trust Him | خيار |
| 34 | الطفل | ✗ أنّ فرعون كان رحيمًا | That Pharaoh was kind | خيار |
| 35 | الطفل | ✗ أن نخاف دائمًا | To always be afraid | خيار |
| 36 | الجدّة آمنة | تلميح: تذكّر: هل تحقّق وعدُ الله لأمّ موسى؟ | Remember: did Allah's promise to Musa's mother come true? | تلميح |
| 37 | الجدّة آمنة | ثناء: ممتاز! وتذكّر حبَّ أمّك لك، فقد كانت أمّ موسى تحبّه كثيرًا. | Excellent! And remember how much your mother loves you — just as Musa's mother loved him. | ثناء |
| 38 | الطفل | سأتوكّل على الله، وأحبّ أمّي وأطيعها! | I'll trust in Allah, and love and obey my mother! | سطر |
| 39 | — | [مكافأة 50 نقطة] تعلّمت قصة موسى عليه السلام الطفل في النهر. | You learned the story of baby Musa, peace be upon him, on the river. | مكافأة |

## 4) عيسى عليه السلام: الكلامُ في المهد — Isa (Jesus): Speaking from the Cradle

- **المعرّف:** `isa-in-the-cradle` · **الفئة/الترتيب:** prophets / 4 · **يُفتح بعد:** `musa-on-the-river` · **المنطقة:** `oasis`
- **الشخصيات والمواضع:** الجدّة زينب (-93.0, -8.1) facing 0.0، جالسة (seat 0.3, yOffset -0.15)
- **الآيات المتلوّة:** 19:30–19:33 — https://quran.com/19/30
- **توجيه الراوي:** روح لعريشة النخيل في الواحة، الجدّة زينب قاعدة في الظلّ مستنياك. — Go to the palm shelter at the oasis — Grandma Zainab is sitting in the shade, waiting for you.
- **التحية:** تعالَ يا حبيبي، اقعد قدّامي في الظلّ تحت النخيل. عندي لك حكاية عن نخلةٍ مباركة. · **بعد الانتهاء:** عيسى عليه السلام عبدُ الله ورسوله، فأحِبَّ الأنبياءَ كلَّهم. · **رسالة القفل:** أهلًا يا حبيبي! اسمع أولًا قصة «موسى الطفل في النهر» عند الترعة الغربية، ثم تعالَ إليّ.
- **المصادر (تظهر في اللعبة):**
  - Qur'an 19:16–36 (https://quran.com/19/16)
  - Qur'an 3:42–47 (https://quran.com/3/42)
  - Qur'an 3:59 (https://quran.com/3/59)
  - Tafsir Ibn Kathir — Surat Maryam
  - Tafsir al-Muyassar — Surat Maryam

**نقاط تحتاج نظر المراجع:**

- سؤال مريم (19:20) صيغ للأطفال: «كيف يكون لي ولدٌ وليس لي زوج؟» وحُذف «ولم أكُ بغيًّا».
- كلام قومها (19:27–28) مذكور مجملًا: «قالوا كلامًا يلومونها فيه».
- المنادي «من تحتها» (19:24) لم يُسمَّ لاختلاف المفسرين (جبريل أو عيسى).
- «برّ الوالدين من أحبّ الأعمال إلى الله» — من حديث ابن مسعود (البخاري 527).
- الجدّة زينب (نموذج جلوس فقط) تجلس على مقعد العريشة في الواحة — يحتاج فحصًا بصريًا في اللعبة.
- ملاحظة البيانات (`_note`): Qur'an-only retelling. For children, Maryam's question (19:20) is given as 'how can I have a son when I have no husband?' and the people's words (19:27–28) only as 'they said words blaming her'. Who called her 'from beneath her' (19:24) is left unnamed (tafsir differs: Jibril or Isa). Verses 19:30–33 are played. Grandma Zainab (sit-only model) sits on the rug bench of the oasis shelter (arish) — needs an in-game visual check (bench top ≈0.30 m vs mastaba 0.45 m, hence yOffset −0.15).

**الحوار كاملًا:**

| # | المتكلّم | النص | English | النوع |
|---|---|---|---|---|
| 1 | الجدّة زينب | أهلًا يا حبيبي! اقعد هنا في الظلّ. هل ترى النخل والرطب؟ في القرآن سورةٌ اسمها سورة «مريم»، فيها قصةٌ عن نخلةٍ مباركة. | Hello, my darling! Sit here in the shade. Can you see the palm trees and the fresh dates? In the Quran there is a surah called “Maryam”, with a story about a blessed palm tree. | سطر |
| 2 | الجدّة زينب | هل تعرف مَن هي مريم؟ | Do you know who Maryam was? | سؤال |
| 3 | الطفل | أمّ عيسى عليه السلام؟ | The mother of Isa, peace be upon him? | الطفل |
| 4 | الجدّة زينب | ↳ أحسنت يا حبيبي! مريم ابنةُ عمران، امرأةٌ صالحةٌ طاهرة، تعبد الله كثيرًا. اختارها الله وطهّرها. | Well done, my darling! Maryam, the daughter of Imran — a good, pure woman who worshipped Allah a great deal. Allah chose her and purified her. | ردّ |
| 5 | الطفل | لا، مَن هي؟ | No — who was she? | الطفل |
| 6 | الجدّة زينب | ↳ هي مريم ابنةُ عمران، أمّ نبيّ الله عيسى عليه السلام، امرأةٌ صالحةٌ طاهرة، اختارها الله وطهّرها. | She was Maryam, the daughter of Imran, mother of Allah's prophet Isa, peace be upon him — a good, pure woman whom Allah chose and purified. | ردّ |
| 7 | الطفل | وماذا حدث لمريم؟ | What happened to Maryam? | الطفل |
| 8 | الجدّة زينب | ↳ بينما كانت مريم وحدها في مكانٍ بعيدٍ عن أهلها، أرسل الله إليها المَلَك جبريل عليه السلام، فبشّرها بأنّ الله سيهب لها ولدًا طاهرًا. | While Maryam was alone, in a place away from her family, Allah sent the angel Jibril, peace be upon him, with good news: Allah would give her a pure son. | ردّ |
| 9 | الطفل | ولد؟ وليس لها زوج؟ | A son? But she had no husband? | الطفل |
| 10 | الجدّة زينب | ↳ هذا ما قالته مريم نفسها: كيف يكون لي ولدٌ وليس لي زوج؟ فقال لها: كذلك قال ربّكِ، هو عليّ هيّن. | That is exactly what Maryam asked: “How can I have a son when I have no husband?” He said: “So it will be — your Lord says: it is easy for Me.” | ردّ |
| 11 | الجدّة زينب | ↳ فالله قادرٌ على كلّ شيء: خلق آدمَ من غير أبٍ ولا أمّ، وخلق عيسى من أمٍّ بلا أب. وإذا أراد شيئًا قال له: كن، فيكون. | Allah can do anything: He created Adam with no father and no mother, and created Isa from a mother with no father. When He wants something, He says to it “Be!” — and it is. | ردّ |
| 12 | الطفل | وأين وُلد عيسى عليه السلام؟ | Where was Isa, peace be upon him, born? | الطفل |
| 13 | الجدّة زينب | ↳ ذهبت مريم إلى مكانٍ بعيد، وجاءتها الولادة عند جذع نخلة، وكانت متعبةً وحزينة. | Maryam went to a far-away place, and the birth came to her by the trunk of a palm tree. She was tired and sad. | ردّ 🖼 `palm_stream` |
| 14 | الجدّة زينب | ↳ فناداها منادٍ من تحتها: لا تحزني! قد جعل ربُّكِ تحتكِ جدولَ ماء، وهُزّي إليكِ بجذع النخلة تتساقط عليكِ رطبًا طازجًا. | Then a voice called to her from below: “Do not be sad! Your Lord has put a little stream beneath you. And shake the trunk of the palm towards you — fresh ripe dates will fall down for you.” | ردّ 🖼 `palm_stream` |
| 15 | الطفل | رطب؟ مثل رطب الواحة؟ | Dates? Like the dates here at the oasis? | الطفل |
| 16 | الجدّة زينب | ↳ نعم يا حبيبي! فأكلت مريم من الرطب، وشربت من الماء، وقرّت عينُها — أي فرحت واطمأنّت. | Yes, my darling! Maryam ate the dates and drank the water, and she was comforted and at peace. | ردّ 🖼 `palm_stream` |
| 17 | الطفل | وماذا قال الناس لمّا رأوها مع الطفل؟ | What did people say when they saw her with the baby? | الطفل |
| 18 | الجدّة زينب | ↳ رجعت مريم إلى قومها تحمل الطفل، فتعجّبوا وقالوا كلامًا يلومونها فيه، لأنّهم لم يعرفوا المعجزة. | Maryam came back to her people carrying the baby. They were amazed and said words blaming her, because they didn't know about the miracle. | ردّ |
| 19 | الجدّة زينب | ↳ وكانت مريم قد نذرت لله أن تصوم عن الكلام ذلك اليوم، فلم تتكلّم، وأشارت إلى الطفل. | Maryam had promised Allah to fast from speaking that day, so she didn't speak — she pointed to the baby. | ردّ |
| 20 | الطفل | إلى الطفل؟! وهل يتكلّم الرضيع؟ | To the baby?! Can a baby talk? | الطفل |
| 21 | الجدّة زينب | ↳ قالوا: كيف نكلّم طفلًا في المهد؟ فأنطق الله عيسى وهو رضيع، فقال: «إنّي عبدُ الله، آتانيَ الكتابَ وجعلني نبيًّا». | They said: “How can we talk to a baby in the cradle?” Then Allah made baby Isa speak, and he said: “I am the servant of Allah. He has given me the Book and made me a prophet.” | ردّ |
| 22 | الجدّة زينب | ↳ وقال: «وجعلني مباركًا أينما كنت… وبَرًّا بوالدتي» — يعني: يُحسن إلى أمّه ويطيعها. | And he said: “He has made me blessed wherever I am… and kind to my mother” — meaning he was good to his mother and obeyed her. | ردّ |
| 23 | الجدّة زينب | ما أوّل ما قاله عيسى عليه السلام في المهد؟ | What were the first words Isa, peace be upon him, said in the cradle? | اختبار |
| 24 | الطفل | ✓ إنّي عبدُ الله | I am the servant of Allah | خيار |
| 25 | الطفل | ✗ أنا ملك | I am a king | خيار |
| 26 | الطفل | ✗ أنا جائع | I am hungry | خيار |
| 27 | الجدّة زينب | تلميح: تذكّر: أوّل ما قاله أنّه عبدٌ لـ… | Remember: the first thing he said was that he is the servant of… | تلميح |
| 28 | الجدّة زينب | ثناء: أحسنت! عيسى عليه السلام عبدُ الله ورسوله، والله واحدٌ لا شريك له. | Well done! Isa, peace be upon him, is the servant and messenger of Allah — and Allah is One, with no partner. | ثناء |
| 29 | الجدّة زينب | تعالَ نسمع كلام عيسى عليه السلام في القرآن، بصوت الشيخ. | Come, let's hear Isa's words, peace be upon him, from the Quran, in the sheikh's voice. | سطر |
| 30 | — | [تلاوة 19:30–19:33] |  | آيات |
| 31 | الجدّة زينب | فماذا نتعلّم من قصة مريم وعيسى عليهما السلام؟ | So what do we learn from the story of Maryam and Isa, peace be upon them? | اختبار |
| 32 | الطفل | ✓ أنّ الله قادرٌ على كلّ شيء، وأن نبرّ أمّهاتنا كما كان عيسى بارًّا بأمّه | Allah can do anything — and we should be kind to our mothers, as Isa was to his | خيار |
| 33 | الطفل | ✗ أنّ الأطفال لا يحبّون أمّهاتهم | That children don't love their mothers | خيار |
| 34 | الطفل | ✗ أنّ المعجزات لا تحدث | That miracles never happen | خيار |
| 35 | الجدّة زينب | تلميح: تذكّر: قال عيسى «وبَرًّا بوالدتي»… | Remember: Isa said “and kind to my mother”… | تلميح |
| 36 | الجدّة زينب | ثناء: ممتاز! برُّ الوالدين من أحبّ الأعمال إلى الله. | Excellent! Being good to your parents is one of the deeds Allah loves most. | ثناء |
| 37 | الطفل | سأكون بارًّا بأمّي، وأحبّ كلّ أنبياء الله! | I'll be good to my mother, and love all of Allah's prophets! | سطر |
| 38 | — | [مكافأة 50 نقطة] تعلّمت قصة عيسى عليه السلام والكلام في المهد. | You learned the story of Isa, peace be upon him, speaking from the cradle. | مكافأة |

## 5) محمد ﷺ: الصادق الأمين — Muhammad ﷺ: The Truthful, the Trustworthy

- **المعرّف:** `muhammad-the-trustworthy` · **الفئة/الترتيب:** prophets / 5 · **يُفتح بعد:** `isa-in-the-cradle` · **المنطقة:** `mountains`
- **الشخصيات والمواضع:** الجدّ سالم (5.0, 125.0) facing 3.1416 · الجدّة آمنة (7.6, 125.6) facing -2.41
- **الآيات المتلوّة:** 96:1–96:5 — https://quran.com/96/1
- **توجيه الراوي:** روح لسفح التلال شمال النهر، الجدّ سالم والجدّة آمنة مستنيينك. — Go to the foot of the hills north of the river — Grandpa Salim and Grandma Amina are waiting for you.
- **التحية:** أهلًا يا بُنيّ! ما أجملَ الهدوء عند التلال… تعالَ نحكي لك عن أحبّ الناس إلينا. · **بعد الانتهاء:** صلِّ على النبيّ ﷺ، واصدُق دائمًا، وارحم مَن حولك. · **رسالة القفل:** أهلًا يا بُنيّ! اسمع أولًا قصة «عيسى والكلام في المهد» في الواحة، ثم تعالَ إلينا.
- **المصادر (تظهر في اللعبة):**
  - Qur'an 96:1–5 (https://quran.com/96/1)
  - Qur'an 21:107 (https://quran.com/21/107)
  - Qur'an 68:4 (https://quran.com/68/4)
  - Qur'an 33:21 (https://quran.com/33/21)
  - صحيح البخاري 3 — حديث عائشة رضي الله عنها في بدء الوحي (https://sunnah.com/bukhari:3)
  - صحيح البخاري 4770 — «ما جرّبنا عليك إلا صدقًا» (https://sunnah.com/bukhari:4770)
  - صحيح البخاري 5997 — «مَن لا يَرحم لا يُرحم» (https://sunnah.com/bukhari:5997)
  - صحيح البخاري 516 — حمله أُمامة في الصلاة (https://sunnah.com/bukhari:516)
  - سيرة ابن هشام — تلقيب قريش له ﷺ «الأمين» قبل البعثة

**نقاط تحتاج نظر المراجع:**

- حُذف من حديث بدء الوحي: «فغطّني حتى بلغ مني الجهد».
- حديث الصفا مستعمل حتى «ما جرّبنا عليك إلا صدقًا» فقط (بلا ردّ أبي لهب).
- لقب «الأمين» قبل البعثة من ابن إسحاق؛ عبارة «الصادق الأمين» هي الصيغة الشائعة — يرجى المراجعة.
- «وفي رمضان» — نزول القرآن في رمضان (2:185)، ولم يُحدَّد اليوم.
- الآيات 21:107 و68:4 و33:21 مذكورة بالمعنى داخل الحوار ولا تُتلى.
- ملاحظة البيانات (`_note`): The Prophet ﷺ is only narrated about. In Hira, the angel pressing him (غطّني حتى بلغ مني الجهد) is left out; 'his heart trembling' and «زمّلوني» are from Bukhari 3. The Safa gathering (Bukhari 4770) is used only up to «ما جربنا عليك إلا صدقا» (Abu Lahab's reply left out). 'Al-Amin' before prophethood is from Ibn Ishaq; the pairing «الصادق الأمين» is the popular phrase — please review. Verses 96:1–5 are played.

**الحوار كاملًا:**

| # | المتكلّم | النص | English | النوع |
|---|---|---|---|---|
| 1 | الجدّ سالم | أهلًا يا بُنيّ! هل تذكر قصة أصحاب الفيل؟ في ذلك العام نفسه وُلد في مكة طفلٌ مبارك: محمد ﷺ، خاتمُ الأنبياء والمرسلين. | Hello, my son! Do you remember the story of the People of the Elephant? In that very year a blessed child was born in Makkah: Muhammad ﷺ, the last of the prophets and messengers. | سطر 🖼 `year` |
| 2 | الجدّة آمنة | هل تعرف بماذا كان يلقّبه أهلُ مكة قبل أن يصير نبيًّا؟ | Do you know what the people of Makkah called him before he became a prophet? | سؤال |
| 3 | الطفل | الصادق الأمين! | The Truthful, the Trustworthy! | الطفل |
| 4 | الجدّة آمنة | ↳ أحسنت يا حبيبي! كانوا يسمّونه «الأمين»، لأنّه لا يكذب أبدًا، ولا يخون الأمانة. | Well done, my darling! They called him “al-Amin”, the Trustworthy, because he never lied and never broke a trust. | ردّ |
| 5 | الطفل | لا، بماذا؟ | No — what? | الطفل |
| 6 | الجدّة آمنة | ↳ كانوا يسمّونه «الأمين»، لأنّه لا يكذب أبدًا، ولا يخون الأمانة. | They called him “al-Amin”, the Trustworthy, because he never lied and never broke a trust. | ردّ |
| 7 | الطفل | وهل كانوا يصدّقونه حقًّا؟ | Did they really believe him? | الطفل |
| 8 | الجدّ سالم | ↳ نعم! جمعهم مرّةً عند جبل الصفا وقال: أرأيتم لو أخبرتكم أنّ خيلًا بالوادي تريد أن تُغير عليكم، أكنتم مصدّقيّ؟ | Yes! Once he gathered them at the hill of Safa and said: “If I told you there were horsemen in the valley about to attack you, would you believe me?” | ردّ 🖼 `kaaba` |
| 9 | الجدّة آمنة | ↳ فقالوا: نعم، «ما جرّبنا عليك إلا صدقًا». يعني: لم يكذب علينا يومًا واحدًا. | They said: “Yes — we have never known you to say anything but the truth.” He had never lied to them, not even once. | ردّ 🖼 `kaaba` |
| 10 | الطفل | وكيف نزل عليه الوحي؟ | How did the revelation first come to him? | الطفل |
| 11 | الجدّ سالم | ↳ كان ﷺ يحبّ أن يخلو بنفسه في غارٍ في جبلٍ اسمه «حِراء»، يتعبّد فيه ليالي كثيرة. | He ﷺ loved to be alone in a cave on a mountain called Hira, worshipping Allah there for many nights. | ردّ 🖼 `hira_cave` |
| 12 | الجدّ سالم | ↳ وفي رمضان، جاءه المَلَك جبريل عليه السلام في الغار، فقال له: «اقرأ». | Then in Ramadan, the angel Jibril, peace be upon him, came to him in the cave and said: “Read!” | ردّ 🖼 `hira_cave` |
| 13 | الطفل | وهل كان يعرف القراءة؟ | Could he read? | الطفل |
| 14 | الجدّة آمنة | ↳ لا! كان ﷺ أمّيًّا لا يقرأ ولا يكتب، فقال: «ما أنا بقارئ». فعلّمه جبريل أوّلَ ما نزل من القرآن: «اقرأ باسم ربّك الذي خلق». | No! He ﷺ could not read or write, so he said: “I cannot read.” Then Jibril taught him the first words of the Quran ever revealed: “Read in the name of your Lord who created.” | ردّ 🖼 `hira_cave` |
| 15 | الجدّ سالم | ↳ فرجع ﷺ إلى بيته وقلبه يرتجف من عِظَم ما رأى، فقال لزوجته خديجة رضي الله عنها: «زمّلوني، زمّلوني» — أي غطّوني. | He ﷺ went home, his heart trembling at the greatness of what he had seen, and said to his wife Khadijah, may Allah be pleased with her: “Cover me, cover me!” | ردّ |
| 16 | الطفل | وماذا قالت له خديجة؟ | What did Khadijah say to him? | الطفل |
| 17 | الجدّة آمنة | ↳ طمأنته وقالت: «كلّا واللهِ ما يُخزيك اللهُ أبدًا؛ إنّك لتصلُ الرحم، وتحملُ الكَلّ، وتُكسبُ المعدوم، وتَقري الضيف، وتُعين على نوائب الحقّ». | She comforted him and said: “No, by Allah, Allah will never let you down. You keep ties with your relatives, you carry the burdens of the weak, you give to those who have nothing, you honour your guests, and you help people through hard times.” | ردّ |
| 18 | الجدّة آمنة | ↳ يعني: أنت تصل أقاربك، وتساعد الضعيف، وتعطي الفقير، وتُكرم الضيف، وتقف مع الناس في المصائب — فالله لن يتركك. | In other words: someone who does all this good — Allah will never abandon him. | ردّ |
| 19 | الجدّ سالم | ما أوّل كلمةٍ نزلت من القرآن؟ | What was the first word of the Quran to be revealed? | اختبار |
| 20 | الطفل | ✓ اقرأ | Read | خيار |
| 21 | الطفل | ✗ اكتب | Write | خيار |
| 22 | الطفل | ✗ نَم | Sleep | خيار |
| 23 | الجدّ سالم | تلميح: كان جبريل يقول له: … باسم ربّك الذي خلق | Jibril said to him: “… in the name of your Lord who created” | تلميح |
| 24 | الجدّ سالم | ثناء: أحسنت! «اقرأ» — ولهذا يحبّ المسلمون العلم والقراءة. | Well done! “Read” — that is why Muslims love knowledge and reading. | ثناء |
| 25 | الطفل | وكيف كان يعامل الأطفال؟ | How did he treat children? | الطفل |
| 26 | الجدّة آمنة | ↳ كان رحيمًا بالأطفال جدًّا. قبّل مرّةً حفيدَه الحسن، فقال رجل: عندي عشرةٌ من الأولاد ما قبّلتُ منهم أحدًا! فقال النبيّ ﷺ: «مَن لا يَرحم لا يُرحم». | He was very gentle with children. Once he kissed his grandson al-Hasan, and a man said: “I have ten children and I have never kissed any of them!” The Prophet ﷺ said: “Whoever does not show mercy will not be shown mercy.” | ردّ |
| 27 | الجدّ سالم | ↳ وكان ﷺ يصلّي وهو يحمل حفيدته أُمامة؛ فإذا سجد وضعها، وإذا قام حملها. | And he ﷺ would pray carrying his granddaughter Umamah: when he bowed down to the ground he put her down, and when he stood up he picked her up again. | ردّ |
| 28 | الطفل | لماذا أرسله الله؟ | Why did Allah send him? | الطفل |
| 29 | الجدّ سالم | ↳ أرسله الله رحمةً للعالمين، أي للناس جميعًا وللخلق كلّهم. ووصفه الله بأنّه على خُلُقٍ عظيم. | Allah sent him as a mercy to all the worlds — to all people and all creation. And Allah describes him as having a truly great character. | ردّ |
| 30 | الجدّة آمنة | ↳ ولهذا كلّما ذكرنا اسمه نقول: صلّى الله عليه وسلّم. | That is why every time we say his name, we say: “sallallahu alayhi wa sallam” — may Allah send blessings and peace upon him. | ردّ |
| 31 | الجدّة آمنة | تعالَ نسمع أوّلَ ما نزل من القرآن، بصوت الشيخ. | Come, let's hear the very first verses of the Quran, in the sheikh's voice. | سطر |
| 32 | — | [تلاوة 96:1–96:5] |  | آيات |
| 33 | الجدّة آمنة | فماذا نتعلّم من سيرة نبيّنا محمد ﷺ؟ | So what do we learn from the life of our Prophet Muhammad ﷺ? | اختبار |
| 34 | الطفل | ✓ أن نكون صادقين أمناء، ونحبّ العلم، ونرحم الناس | To be truthful and trustworthy, love learning, and be merciful to people | خيار |
| 35 | الطفل | ✗ أن نكذب إذا خفنا | To lie when we're scared | خيار |
| 36 | الطفل | ✗ أن نترك القراءة | To give up reading | خيار |
| 37 | الجدّة آمنة | تلميح: تذكّر: بماذا لقّبه أهل مكة؟ وما أوّل كلمةٍ نزلت؟ | Remember what the people of Makkah called him — and the first word revealed. | تلميح |
| 38 | الجدّة آمنة | ثناء: ممتاز! قال الله: «لقد كان لكم في رسول الله أسوةٌ حسنة». | Excellent! Allah says: “In the Messenger of Allah you have an excellent example.” | ثناء |
| 39 | الطفل | اللهمّ صلِّ وسلّم على نبيّنا محمد! سأكون صادقًا أمينًا. | O Allah, send blessings and peace upon our Prophet Muhammad! I will be truthful and trustworthy. | سطر |
| 40 | — | [مكافأة 50 نقطة] تعلّمت عن نبيّنا محمد ﷺ الصادق الأمين. | You learned about our Prophet Muhammad ﷺ, the Truthful, the Trustworthy. | مكافأة |


---

# قصص الصحابة — Stories of the Companions

## 6) أبو بكر الصدّيق: صاحبُ الغار — Abu Bakr al-Siddiq: The Companion in the Cave

- **المعرّف:** `abu-bakr-the-cave` · **الفئة/الترتيب:** companions / 1 · **يُفتح بعد:** — (أول الفئة) · **المنطقة:** `ruins`
- **الشخصيات والمواضع:** العمّ حمدان (156.0, -120.0) facing 0.0
- **الآيات المتلوّة:** 9:40–9:40 — https://quran.com/9/40
- **توجيه الراوي:** روح للعمّ حمدان على طريق الدار القديمة، مستنيك قبل الأطلال. — Go to Uncle Hamdan on the road to the Old Homestead — he is waiting just before the ruins.
- **التحية:** أهلًا يا صغيري! تعالَ، أحكي لك عن أعظم رحلة، وعن صاحبٍ وفيّ. · **بعد الانتهاء:** الله معنا دائمًا، فلا تحزن ولا تخف.
- **المصادر (تظهر في اللعبة):**
  - Qur'an 9:40 (https://quran.com/9/40)
  - صحيح البخاري 3653 — حديث أبي بكر رضي الله عنه في الغار (https://sunnah.com/bukhari:3653)؛ صحيح مسلم 2381
  - صحيح البخاري 3905 — حديث عائشة رضي الله عنها في الهجرة: غار ثور، عبد الله بن أبي بكر، عامر بن فهيرة، نطاق أسماء (https://sunnah.com/bukhari:3905)
  - صحيح البخاري 3615 — حديث البراء عن أبي بكر في طريق الهجرة (https://sunnah.com/bukhari:3615)
  - Tafsir Ibn Kathir — 9:40

**نقاط تحتاج نظر المراجع:**

- «أوّل من آمن به من الرجال» — المشهور في السيرة؛ يرجى التأكد من الصياغة.
- تفسير لقب «الصدّيق» مبسّط (لم تُذكر قصة الإسراء).
- عبارة «حتى وقفوا فوق الغار» من معنى الحديث: «لو أن أحدهم نظر تحت قدميه لأبصرنا» (البخاري 3653)، وفي مسلم: «نظرت إلى أقدام المشركين على رؤوسنا».
- لم تُستعمل قصة نسج العنكبوت وبيض الحمام ولدغة الحيّة (لا تثبت بإسناد صحيح).
- «أختها أسماء»: الضمير يعود على عائشة رضي الله عنها (الراوية) المذكورة في السطر السابق.
- ملاحظة البيانات (`_note`): Only Bukhari/Muslim details are used. Deliberately NOT used (weak/unestablished): the spider's web and nesting doves at the cave mouth, the snake biting Abu Bakr's foot. The pursuers are only 'people from Makkah looking for them'. Whole 9:40 is played.

**الحوار كاملًا:**

| # | المتكلّم | النص | English | النوع |
|---|---|---|---|---|
| 1 | العمّ حمدان | أهلًا يا صغيري! أنا أحبّ السفر كثيرًا. لكنّي اليوم سأحكي لك عن رحلةٍ عظيمة: رحلة الهجرة، حين خرج نبيّنا محمد ﷺ من مكة إلى المدينة. | Hello, little one! I love travelling. But today I will tell you about a great journey: the Hijra, when our Prophet Muhammad ﷺ left Makkah for Madinah. | سطر |
| 2 | العمّ حمدان | هل تعرف مَن كان صاحبَه في هذه الرحلة؟ | Do you know who travelled with him on this journey? | سؤال |
| 3 | الطفل | أبو بكر الصدّيق؟ | Abu Bakr al-Siddiq? | الطفل |
| 4 | العمّ حمدان | ↳ أحسنت! أبو بكر الصدّيق رضي الله عنه، أقربُ أصحابه إليه، وأوّلُ مَن آمن به من الرجال. | Well done! Abu Bakr al-Siddiq, may Allah be pleased with him — his closest companion, and the first grown man to believe in him. | ردّ |
| 5 | الطفل | لا، مَن هو؟ | No — who was it? | الطفل |
| 6 | العمّ حمدان | ↳ إنّه أبو بكر الصدّيق رضي الله عنه، أقربُ أصحابه إليه، وأوّلُ مَن آمن به من الرجال. | It was Abu Bakr al-Siddiq, may Allah be pleased with him — his closest companion, and the first grown man to believe in him. | ردّ |
| 7 | الطفل | ولماذا سُمّي «الصدّيق»؟ | Why was he called “al-Siddiq”? | الطفل |
| 8 | العمّ حمدان | ↳ لأنّه كان يُصدّق النبيَّ ﷺ في كلّ ما يُخبر به عن الله، بلا تردّد. والصدّيق هو الذي يَصدُق كثيرًا ويُصدِّق بالحقّ. | Because he believed the Prophet ﷺ in everything he told from Allah, without hesitating. “Siddiq” means someone who is always truthful and always believes the truth. | ردّ |
| 9 | الطفل | ولماذا خرج النبيّ ﷺ من مكة؟ | Why did the Prophet ﷺ leave Makkah? | الطفل |
| 10 | العمّ حمدان | ↳ لأنّ كثيرًا من أهل مكة آذَوه وآذَوا المسلمين، وأرادوا أن يمنعوه من الدعوة إلى الله. فأذِن الله له أن يهاجر إلى المدينة، حيث ينتظره أهلُها الذين آمنوا به. | Because many people in Makkah hurt him and the Muslims, and tried to stop him calling people to Allah. So Allah allowed him to emigrate to Madinah, where the believers there were waiting for him. | ردّ 🖼 `year` |
| 11 | الطفل | وكيف استعدّ أبو بكر للرحلة؟ | How did Abu Bakr get ready for the journey? | الطفل |
| 12 | العمّ حمدان | ↳ حكت عائشة رضي الله عنها أنّ أبا بكر جهّز ناقتين للسفر، واستأجرا رجلًا خبيرًا بالطريق ليدلّهما. | Aisha, may Allah be pleased with her, told that Abu Bakr had two camels ready for the road, and they hired a man who knew the way well to guide them. | ردّ 🖼 `hijra_road` |
| 13 | العمّ حمدان | ↳ وقطعت أختُها أسماءُ بنتُ أبي بكر قطعةً من نطاقها — أي حزامها — فربطت بها فمَ كيس الطعام، فسُمّيت «ذات النطاقين». | And her sister Asma', Abu Bakr's daughter, cut a piece from her belt to tie the mouth of the food bag — so she was called “the one with the two belts”. | ردّ 🖼 `hijra_road` |
| 14 | الطفل | وأين اختبآ؟ | Where did they hide? | الطفل |
| 15 | العمّ حمدان | ↳ في غارٍ في جبلٍ اسمه «ثَور»، قريبًا من مكة. بقيا فيه ثلاث ليال. | In a cave in a mountain called Thawr, near Makkah. They stayed there three nights. | ردّ 🖼 `cave_thawr` |
| 16 | العمّ حمدان | ↳ وكان عبدُ الله بن أبي بكر، وهو شابٌّ ذكيّ، يبيت عندهما ويخبرهما بالأخبار، ويرجع إلى مكة قبل الصبح. وكان عامرُ بن فُهيرة يرعى الغنم قريبًا منهما، فيشربان من لبنها. | Abdullah, Abu Bakr's clever young son, spent the nights with them and brought them the news, then went back to Makkah before dawn. And 'Amir ibn Fuhayra grazed sheep nearby, so they could drink their milk. | ردّ 🖼 `cave_thawr` |
| 17 | الطفل | وهل جاء أحدٌ يبحث عنهما؟ | Did anyone come looking for them? | الطفل |
| 18 | العمّ حمدان | ↳ نعم، خرج أناسٌ من مكة يبحثون عنهما، حتى وقفوا فوق الغار! فقال أبو بكر رضي الله عنه: يا رسول الله، لو أنّ أحدهم نظر تحت قدميه لرآنا. | Yes — people from Makkah went out searching, until they were standing right above the cave! Abu Bakr said: “O Messenger of Allah, if one of them looked down at his feet, he would see us.” | ردّ 🖼 `cave_thawr` |
| 19 | العمّ حمدان | ↳ فقال النبيّ ﷺ بطمأنينة: «ما ظنُّك يا أبا بكر باثنين اللهُ ثالثُهما؟» يعني: لا تخف، فالله معنا يحفظنا. | The Prophet ﷺ answered calmly: “What do you think, Abu Bakr, of two when Allah is the third of them?” Meaning: don’t be afraid — Allah is with us, protecting us. | ردّ 🖼 `cave_thawr` |
| 20 | العمّ حمدان | ماذا قال النبيّ ﷺ لأبي بكر في الغار؟ | What did the Prophet ﷺ tell Abu Bakr in the cave? | اختبار |
| 21 | الطفل | ✓ لا تحزن، إنّ الله معنا | Don't be sad — Allah is with us | خيار |
| 22 | الطفل | ✗ اهرب بسرعة | Run away quickly | خيار |
| 23 | الطفل | ✗ نَم ولا تتكلّم | Go to sleep and say nothing | خيار |
| 24 | العمّ حمدان | تلميح: تذكّر: مَن كان «ثالثَهما» في الغار؟ | Remember: who was “the third” with them in the cave? | تلميح |
| 25 | العمّ حمدان | ثناء: أحسنت! الله كان معهما يحفظهما، فلم يرهما أحد. | Well done! Allah was with them, protecting them — and no one saw them. | ثناء |
| 26 | الطفل | وهل وصلا إلى المدينة؟ | Did they reach Madinah? | الطفل |
| 27 | العمّ حمدان | ↳ نعم، حفظهما الله حتى وصلا إلى المدينة سالمَين، واستقبلهما أهلها بفرحٍ عظيم. وكان أبو بكر رضي الله عنه في الطريق يحرص على راحة النبيّ ﷺ ويخدمه بنفسه. | Yes. Allah kept them safe until they reached Madinah, and its people welcomed them with great joy. All along the way, Abu Bakr looked after the Prophet's ﷺ comfort and served him himself. | ردّ 🖼 `hijra_road` |
| 28 | العمّ حمدان | وقد ذكر الله هذه اللحظة في القرآن: «ثانيَ اثنين إذ هما في الغار، إذ يقول لصاحبه لا تحزن إنّ الله معنا». تعالَ نسمع الآية بصوت الشيخ. | Allah mentions this moment in the Quran: “the second of two, when they were in the cave, when he said to his companion: Do not be sad, Allah is with us.” Come, let’s hear the verse in the sheikh’s voice. | سطر |
| 29 | — | [تلاوة 9:40–9:40] |  | آيات |
| 30 | العمّ حمدان | فماذا نتعلّم من قصة الغار؟ | So what do we learn from the story of the cave? | اختبار |
| 31 | الطفل | ✓ أنّ الله معنا دائمًا فنتوكّل عليه، وأن نكون أصدقاء أوفياء | Allah is always with us so we trust Him — and we should be loyal friends | خيار |
| 32 | الطفل | ✗ أن نخاف إذا كنّا وحدنا | To be afraid when we are alone | خيار |
| 33 | الطفل | ✗ أن نترك أصدقاءنا وقت الشدّة | To leave our friends when things get hard | خيار |
| 34 | العمّ حمدان | تلميح: تذكّر: ماذا قال النبيّ ﷺ لصاحبه؟ وهل ترك أبو بكر صاحبه؟ | Remember what the Prophet ﷺ told his companion — and did Abu Bakr ever leave him? | تلميح |
| 35 | العمّ حمدان | ثناء: ممتاز! وكان أبو بكر صديقًا وفيًّا، بقي مع صاحبه في وقت الشدّة. | Excellent! And Abu Bakr was a loyal friend who stayed with his companion in the hardest time. | ثناء |
| 36 | الطفل | إذا خفتُ سأتذكّر: إنّ الله معنا! | When I'm afraid I'll remember: Allah is with us! | سطر |
| 37 | — | [مكافأة 50 نقطة] تعلّمت قصة أبي بكر الصدّيق في الغار. | You learned the story of Abu Bakr al-Siddiq in the cave. | مكافأة |

## 7) عمر بن الخطّاب: الأمير الرحيم — Umar ibn al-Khattab: The Caring Leader

- **المعرّف:** `umar-and-the-widow` · **الفئة/الترتيب:** companions / 2 · **يُفتح بعد:** `abu-bakr-the-cave` · **المنطقة:** `village`
- **الشخصيات والمواضع:** العمّ حمدان (12.0, -4.2) facing 0.8 · الجدّة آمنة (13.8, -6.4) facing 0.0
- **الآيات المتلوّة:** 93:9–93:10 — https://quran.com/93/9
- **توجيه الراوي:** روح للسوق جنب دكّان القرية، العمّ حمدان والجدّة آمنة مستنيينك. — Go to the market by the village stall — Uncle Hamdan and Grandma Amina are waiting for you.
- **التحية:** أهلًا يا صغيري! السوق مزدحم اليوم… وهذا يذكّرني بقصةٍ حدثت في سوق المدينة. · **بعد الانتهاء:** ساعِد المحتاج، واسأل عن حال مَن حولك. · **رسالة القفل:** أهلًا يا صغيري! اسمع أولًا قصة «أبي بكر الصدّيق» على طريق الدار القديمة، ثم تعالَ إلينا.
- **المصادر (تظهر في اللعبة):**
  - صحيح البخاري 4160–4161 — حديث أسلم مولى عمر: المرأة الغفارية في السوق (https://sunnah.com/bukhari:4160)
  - Qur'an 93:9–10 (https://quran.com/93/9)
  - Tafsir Ibn Kathir — Surat al-Duha

**نقاط تحتاج نظر المراجع:**

- حُذف للأطفال: «وخشيت أن تأكلهم الضبع» و«ثكلتك أمك».
- جواب عمر عن أبيها وأخيها (حاصرا حصنًا زمانًا فافتتحاه) صيغ بمعناه: «بذلا الكثير في خدمة المسلمين ونحن ما زلنا ننتفع بما قدّماه».
- تفسير لقب «الفاروق» بأنه يفرّق بين الحق والباطل: شرح مشهور.
- لم تُستعمل قصة «المرأة التي تطبخ الحجارة لأطفالها» لضعف إسنادها.
- مناسبة الآيتين 93:9–10 للقصة مناسبة معنى (الوصية باليتيم والسائل)، وليستا سبب نزول لها.
- ملاحظة البيانات (`_note`): Aslam's narration (Bukhari 4160) as in the Sahih. Left out for children: «وخشيت أن تأكلهم الضبع» and «ثكلتك أمك». Umar's answer about her father and brother (who besieged a fortress) is paraphrased as 'they gave much in serving the Muslims and we still benefit from it'. The famous story of Umar carrying flour at night to the woman cooking stones is NOT used (weak chain). Verses 93:9–10 are played.

**الحوار كاملًا:**

| # | المتكلّم | النص | English | النوع |
|---|---|---|---|---|
| 1 | العمّ حمدان | أهلًا يا صغيري! تعالَ بين الدكاكين. هل تعلم أنّ أميرَ المؤمنين عمرَ بن الخطّاب رضي الله عنه كان يخرج إلى السوق ويمشي بين الناس؟ | Hello, little one! Come among the stalls. Did you know that the leader of the believers, Umar ibn al-Khattab, may Allah be pleased with him, used to go out to the market and walk among the people? | سطر |
| 2 | الجدّة آمنة | هل تعرف مَن هو عمر بن الخطّاب؟ | Do you know who Umar ibn al-Khattab was? | سؤال |
| 3 | الطفل | صاحبُ النبيّ ﷺ؟ | A companion of the Prophet ﷺ? | الطفل |
| 4 | الجدّة آمنة | ↳ نعم يا حبيبي. هو من أقرب أصحاب النبيّ ﷺ، وصار خليفةَ المسلمين بعد أبي بكر الصدّيق رضي الله عنهما. ولُقّب «الفاروق» لأنّه يفرّق بين الحقّ والباطل. | Yes, my darling. He was one of the Prophet's ﷺ closest companions, and became the leader of the Muslims after Abu Bakr. He was called “al-Faruq”, because he told right apart from wrong. | ردّ |
| 5 | الطفل | لا، مَن هو؟ | No — who was he? | الطفل |
| 6 | الجدّة آمنة | ↳ هو من أقرب أصحاب النبيّ ﷺ، وصار خليفةَ المسلمين بعد أبي بكر الصدّيق رضي الله عنهما. ولُقّب «الفاروق» لأنّه يفرّق بين الحقّ والباطل. | He was one of the Prophet's ﷺ closest companions, and became the leader of the Muslims after Abu Bakr. He was called “al-Faruq”, because he told right apart from wrong. | ردّ |
| 7 | الطفل | وكيف كان مع الناس؟ | What was he like with people? | الطفل |
| 8 | الجدّة آمنة | ↳ كان قويًّا في الحقّ، رحيمًا بالضعفاء، يخاف الله كثيرًا، ويشعر أنّه مسؤولٌ عن كلّ واحدٍ من الناس. | He was firm about what is right and gentle with the weak. He feared Allah greatly, and felt responsible for every single person. | ردّ |
| 9 | الطفل | وماذا حدث في السوق؟ | What happened in the market? | الطفل |
| 10 | العمّ حمدان | ↳ حكى أسلمُ، خادمُ عمر: خرجتُ مع عمر إلى السوق، فلحقته امرأةٌ شابّة فقالت: يا أمير المؤمنين، مات زوجي وترك أطفالًا صغارًا، ليس عندهم زرعٌ ولا غنم. | Aslam, Umar's helper, told: I went out with Umar to the market, and a young woman caught up with him and said: “O leader of the believers, my husband has died and left little children. They have no crops and no sheep.” | ردّ |
| 11 | الجدّة آمنة | ↳ وقالت: أنا بنتُ خُفاف بن إيماء الغِفاريّ، وقد شهد أبي الحديبية مع النبيّ ﷺ. | And she said: “I am the daughter of Khufaf ibn Ima' al-Ghifari — my father was with the Prophet ﷺ at al-Hudaybiyah.” | ردّ |
| 12 | الطفل | وهل تركها عمر ومضى؟ | Did Umar just walk on? | الطفل |
| 13 | العمّ حمدان | ↳ لا! وقف معها عمر ولم يمضِ، وقال: «مرحبًا بنسبٍ قريب». ثم ذهب إلى جملٍ قويٍّ كان مربوطًا في الدار. | No! Umar stopped with her and didn't walk on. He said: “Welcome to a family close to us.” Then he went to a strong camel tied up in the yard. | ردّ 🖼 `food_camel` |
| 14 | الجدّة آمنة | ↳ فحمّل عليه كيسين كبيرين ملأهما طعامًا، ووضع بينهما مالًا وثيابًا، ثم أعطاها زمامه وقال: «اقتاديه، فلن يفنى حتى يأتيكم الله بخير». | He loaded it with two big sacks full of food, put money and clothes between them, handed her the rope and said: “Lead it home — it won't run out before Allah brings you something good.” | ردّ 🖼 `food_camel` |
| 15 | العمّ حمدان | ماذا أعطى عمرُ المرأةَ وأطفالها؟ | What did Umar give the woman and her children? | اختبار |
| 16 | الطفل | ✓ جملًا محمّلًا بالطعام والمال والثياب | A camel loaded with food, money and clothes | خيار |
| 17 | الطفل | ✗ درهمًا واحدًا | One single coin | خيار |
| 18 | الطفل | ✗ لم يعطها شيئًا | Nothing at all | خيار |
| 19 | العمّ حمدان | تلميح: تذكّر: ماذا حمّل على الجمل القويّ؟ | Remember what he loaded onto the strong camel… | تلميح |
| 20 | العمّ حمدان | ثناء: أحسنت! أعطاها عطاءً كثيرًا يكفي أطفالها. | Well done! He gave her plenty — enough for her children. | ثناء |
| 21 | الطفل | ألم يقل له أحدٌ إنّه أعطاها كثيرًا؟ | Didn't anyone say he gave her too much? | الطفل |
| 22 | العمّ حمدان | ↳ بلى، قال رجل: يا أمير المؤمنين، أكثرتَ لها! فقال عمر: إنّ أباها وأخاها بذلا الكثير في خدمة المسلمين، ونحن ما زلنا ننتفع بما قدّماه. | Yes — a man said: “O leader of the believers, you gave her too much!” Umar said: her father and brother gave a great deal in serving the Muslims, and we are still benefiting from what they did. | ردّ |
| 23 | الجدّة آمنة | ↳ يعني: أهلُ الخير لا يُنسى خيرُهم، ونحن نحفظ الجميل لأولادهم. | Meaning: good people's kindness is never forgotten — we repay it to their children. | ردّ |
| 24 | الطفل | ولماذا اهتمّ عمر بها كلَّ هذا الاهتمام؟ | Why did Umar care so much? | الطفل |
| 25 | الجدّة آمنة | ↳ لأنّ الله أوصانا باليتيم والمحتاج. وأطفالها صاروا أيتامًا — واليتيم هو الطفل الذي مات أبوه. | Because Allah tells us to look after orphans and people in need. Her children had become orphans — an orphan is a child whose father has died. | ردّ |
| 26 | الجدّة آمنة | ↳ وفي القرآن آيتان تقولان لنا: أكرِم اليتيم ولا تقسُ عليه، وكلِّم مَن يسألك حاجةً برفق. | And two verses of the Quran tell us: be kind to the orphan and never harsh, and speak gently to anyone who asks you for help. | ردّ |
| 27 | الجدّة آمنة | تعالَ نسمع الآيتين بصوت الشيخ. | Come, let's hear the two verses in the sheikh's voice. | سطر |
| 28 | — | [تلاوة 93:9–93:10] |  | آيات |
| 29 | الجدّة آمنة | فماذا نتعلّم من قصة عمر رضي الله عنه؟ | So what do we learn from the story of Umar? | اختبار |
| 30 | الطفل | ✓ أن نرحم اليتيم والمحتاج ونساعدهم | To be kind to orphans and people in need, and help them | خيار |
| 31 | الطفل | ✗ أن نمشي في السوق بسرعة | To walk quickly through the market | خيار |
| 32 | الطفل | ✗ أن نساعد فقط مَن نعرفه | To help only people we know | خيار |
| 33 | الجدّة آمنة | تلميح: تذكّر: ماذا فعل عمر حين سمع حاجة المرأة؟ | Remember what Umar did when he heard what the woman needed… | تلميح |
| 34 | الجدّة آمنة | ثناء: ممتاز! القائد الحقّ يرحم الناس ويسأل عن حالهم، وأنت أيضًا تستطيع أن تساعد. | Excellent! A true leader is kind to people and asks how they are — and you can help too. | ثناء |
| 35 | الطفل | سأساعد مَن يحتاج، وأكون رحيمًا بالأيتام! | I'll help anyone in need, and be kind to orphans! | سطر |
| 36 | — | [مكافأة 50 نقطة] تعلّمت قصة عمر بن الخطّاب الأمير الرحيم. | You learned the story of Umar ibn al-Khattab, the caring leader. | مكافأة |

## 8) عثمان بن عفّان: بئرُ رُومة — Uthman ibn Affan: The Well of Rumah

- **المعرّف:** `uthman-and-the-well` · **الفئة/الترتيب:** companions / 3 · **يُفتح بعد:** `umar-and-the-widow` · **المنطقة:** `village`
- **الشخصيات والمواضع:** الجدّ سالم (-5.0, 7.2) facing 0.0
- **الآيات المتلوّة:** 2:261–2:261 — https://quran.com/2/261
- **توجيه الراوي:** روح لبئر القرية في الساحة، الجدّ سالم مستنيك جنب البئر. — Go to the village well on the square — Grandpa Salim is waiting by the well.
- **التحية:** أهلًا يا بُنيّ! تعالَ عند البئر… ما أطيبَ الماء البارد! · **بعد الانتهاء:** ما تُنفقه في الخير يكبر عند الله، مثل حبّة القمح. · **رسالة القفل:** أهلًا يا بُنيّ! اسمع أولًا قصة «عمر بن الخطّاب» في السوق، ثم تعالَ إليّ.
- **المصادر (تظهر في اللعبة):**
  - جامع الترمذي 3703 — مناشدة عثمان رضي الله عنه: «من يشتري بئر رومة…» (حسن) (https://sunnah.com/tirmidhi:3703)؛ والنسائي 3608
  - صحيح البخاري 2778 — «من حفر رومة فله الجنة» و«من جهّز جيش العسرة فله الجنة» (https://sunnah.com/bukhari:2778)؛ وعلّقه البخاري في كتاب المساقاة (https://sunnah.com/bukhari/42)
  - Qur'an 2:261 (https://quran.com/2/261)
  - Tafsir Ibn Kathir — 2:261

**نقاط تحتاج نظر المراجع:**

- تفاصيل مالك البئر والثمن وشراء النصف أولًا غير مذكورة (ليست في الروايات المعتمدة هنا).
- «جهّز من ماله الكثيرين في وقت شدّة وعسرة» = تجهيز جيش العسرة (البخاري 2778) بلا ذكر للقتال.
- مناسبة 2:261 للقصة مناسبة معنى (فضل الإنفاق)، وليست سبب نزول.
- سؤال الحساب (سبعمئة) من مثال الآية نفسه.
- ملاحظة البيانات (`_note`): Tirmidhi 3703 (hasan): «قدم المدينة وليس بها ماء يستعذب غير بئر رومة… فاشتريتها من صلب مالي». Not used: the popular details about the owner, the price and buying half the well first. The 'army of hardship' is only mentioned as 'equipped many in a time of hardship'. Dhu al-Nurayn: married two of the Prophet's ﷺ daughters (Ruqayyah, then Umm Kulthum). Whole 2:261 is played.

**الحوار كاملًا:**

| # | المتكلّم | النص | English | النوع |
|---|---|---|---|---|
| 1 | الجدّ سالم | أهلًا يا بُنيّ! نحن في القرية نحمد الله على هذا البئر؛ منه نشرب ونسقي. تخيّل مدينةً كاملة ليس فيها ماءٌ عذبٌ إلا بئرٌ واحدة! | Hello, my son! In our village we thank Allah for this well — we drink from it and water our plants. Imagine a whole town with only one well of sweet water! | سطر |
| 2 | الجدّ سالم | هل سمعتَ ببئر «رُومة»؟ | Have you heard of the well of Rumah? | سؤال |
| 3 | الطفل | لا يا جدّي، ما قصتها؟ | No, Grandpa — what's its story? | الطفل |
| 4 | الجدّ سالم | ↳ اسمع يا بُنيّ، هي قصة صحابيٍّ كريمٍ جدًّا. | Listen, my son — it is the story of a very generous companion. | ردّ |
| 5 | الطفل | بئرٌ في المدينة؟ | A well in Madinah? | الطفل |
| 6 | الجدّ سالم | ↳ نعم! بئرٌ في المدينة المنوّرة، ولها قصةٌ جميلة. | Yes! A well in Madinah, and it has a beautiful story. | ردّ |
| 7 | الطفل | ولماذا كانت هذه البئر مهمّة؟ | Why was this well so important? | الطفل |
| 8 | الجدّ سالم | ↳ لمّا قدم النبيّ ﷺ المدينة، لم يكن فيها ماءٌ عذبٌ طيّب إلا بئر رومة، وكانت ملكًا لرجل، والناس يحتاجون إلى مائها. | When the Prophet ﷺ came to Madinah, the only sweet, fresh water there was the well of Rumah. It belonged to one man, and people needed its water. | ردّ 🖼 `well_rumah` |
| 9 | الطفل | وماذا قال النبيّ ﷺ؟ | What did the Prophet ﷺ say? | الطفل |
| 10 | الجدّ سالم | ↳ قال رسول الله ﷺ: «مَن يشتري بئرَ رومة، فيجعلُ دلوَه مع دِلاء المسلمين، بخيرٍ له منها في الجنة؟» | The Messenger of Allah ﷺ said: “Who will buy the well of Rumah and put his bucket in it alongside the buckets of the Muslims — for something better than it in Paradise?” | ردّ 🖼 `well_rumah` |
| 11 | الجدّ سالم | ↳ يعني: مَن يشتريها ويجعل ماءها للناس جميعًا، يشرب منها مثلهم، وله أجرٌ أعظم في الجنة. | Meaning: whoever buys it and gives its water to everyone — drinking from it just like them — will have a far greater reward in Paradise. | ردّ 🖼 `well_rumah` |
| 12 | الطفل | ومَن اشتراها؟ | Who bought it? | الطفل |
| 13 | الجدّ سالم | ↳ عثمانُ بن عفّان رضي الله عنه! قال: «فاشتريتُها من صُلب مالي» — أي من ماله الخاص. وجعل ماءها لكلّ المسلمين. | Uthman ibn Affan, may Allah be pleased with him! He said: “I bought it with my own money.” And he gave its water to all the Muslims. | ردّ 🖼 `well_rumah` |
| 14 | الطفل | هل كان عثمان كريمًا في أشياء أخرى؟ | Was Uthman generous in other ways too? | الطفل |
| 15 | الجدّ سالم | ↳ نعم يا بُنيّ! كان من أكرم الصحابة. جهّز من ماله الكثيرين في وقت شدّةٍ وعُسرة، ووسّع مسجدَ النبيّ ﷺ. | Yes, my son! He was one of the most generous companions. With his own money he equipped many people in a time of hardship, and he enlarged the Prophet's ﷺ mosque. | ردّ |
| 16 | الجدّ سالم | ↳ وكان يُلقَّب «ذا النورين»، لأنّه تزوّج ابنتين من بنات النبيّ ﷺ، واحدةً بعد الأخرى. | He was called “Dhu al-Nurayn” — the one with two lights — because he married two of the Prophet's ﷺ daughters, one after the other. | ردّ |
| 17 | الطفل | وكيف يكبر أجرُ الصدقة يا جدّي؟ | Grandpa, how does the reward of giving grow? | الطفل |
| 18 | الجدّ سالم | ↳ أنا فلّاح، وأعرف هذا جيّدًا! أزرع حبّةَ قمحٍ واحدة، فتنبت سنابل. والله ضرب لنا مثلًا في القرآن: حبّةٌ واحدة تُنبت سبعَ سنابل، في كلّ سنبلةٍ مئةُ حبّة! | I'm a farmer — I know this well! I plant one grain of wheat and ears of wheat grow. Allah gives us an example in the Quran: one grain grows seven ears, and every ear has a hundred grains! | ردّ 🖼 `seven_ears` |
| 19 | الجدّ سالم | ↳ هكذا يضاعف الله أجرَ مَن ينفق مالَه في الخير، والله يضاعف لمن يشاء. | That is how Allah multiplies the reward of those who spend their money on good — and Allah multiplies it even more for whom He wills. | ردّ 🖼 `seven_ears` |
| 20 | الجدّ سالم | تعالَ نسمع هذه الآية بصوت الشيخ. | Come, let's hear this verse in the sheikh's voice. | سطر |
| 21 | — | [تلاوة 2:261–2:261] |  | آيات |
| 22 | الجدّ سالم | في مثال الآية: كم حبّةً تصير الحبّةُ الواحدة؟ | In the verse's example, how many grains does one grain become? | اختبار |
| 23 | الطفل | ✓ سبعمئة حبّة | Seven hundred grains | خيار |
| 24 | الطفل | ✗ حبّتين | Two grains | خيار |
| 25 | الطفل | ✗ عشر حبّات | Ten grains | خيار |
| 26 | الجدّ سالم | تلميح: سبعُ سنابل، في كلّ سنبلةٍ مئةُ حبّة… | Seven ears, and a hundred grains in every ear… | تلميح |
| 27 | الجدّ سالم | ثناء: ممتاز! سبعةٌ في مئة = سبعمئة، والله يضاعف أكثر لمن يشاء. | Excellent! Seven times a hundred is seven hundred — and Allah multiplies even more for whom He wills. | ثناء |
| 28 | الجدّ سالم | فماذا نتعلّم من قصة عثمان رضي الله عنه؟ | So what do we learn from the story of Uthman? | اختبار |
| 29 | الطفل | ✓ أن ننفق في الخير ونشارك الناس ما ينفعهم | To give for good and share what helps people | خيار |
| 30 | الطفل | ✗ أن نحتفظ بكلّ شيءٍ لأنفسنا | To keep everything for ourselves | خيار |
| 31 | الطفل | ✗ أن نبيع الماء للعطشان بثمنٍ غالٍ | To sell water to thirsty people for a high price | خيار |
| 32 | الجدّ سالم | تلميح: تذكّر: لمن جعل عثمانُ ماءَ البئر؟ | Remember who Uthman gave the well water to… | تلميح |
| 33 | الجدّ سالم | ثناء: ممتاز! حتى كوبُ ماءٍ تقدّمه لعطشان صدقةٌ جميلة. | Excellent! Even a cup of water you give a thirsty person is a lovely charity. | ثناء |
| 34 | الطفل | سأسقي العطشان، وأشارك ما عندي! | I'll give water to the thirsty and share what I have! | سطر |
| 35 | — | [مكافأة 50 نقطة] تعلّمت قصة عثمان بن عفّان وبئر رومة. | You learned the story of Uthman ibn Affan and the well of Rumah. | مكافأة |

## 9) عليّ بن أبي طالب: ليلةُ الهجرة والأمانات — Ali ibn Abi Talib: The Night of the Hijra and the Trusts

- **المعرّف:** `ali-and-the-trusts` · **الفئة/الترتيب:** companions / 4 · **يُفتح بعد:** `uthman-and-the-well` · **المنطقة:** `village`
- **الشخصيات والمواضع:** الجدّة آمنة (-26.7, -15.8) facing 1.5708
- **دعائم:** lantern (-27.95, -17.3)
- **الآيات المتلوّة:** 4:58–4:58 (الكلمات 1–8 فقط) — https://quran.com/4/58
- **توجيه الراوي:** زور الجدّة آمنة عند باب البيت اللي عليه فانوس، غرب ساحة القرية. — Visit Grandma Amina at the door with the lantern, west of the village square.
- **التحية:** أهلًا يا حبيبي! هل تعرف معنى «الأمانة»؟ تعالَ، عندي لك قصة. · **بعد الانتهاء:** ردَّ الأمانةَ إلى صاحبها، ولو كانت شيئًا صغيرًا. · **رسالة القفل:** أهلًا يا حبيبي! اسمع أولًا قصة «عثمان وبئر رومة» عند بئر القرية، ثم تعالَ إليّ.
- **المصادر (تظهر في اللعبة):**
  - سيرة ابن هشام (عن ابن إسحاق) — مبيت عليّ على فراش النبي ﷺ و«نم على فراشي وتسجَّ ببردي هذا…» (https://www.islamweb.net/ar/library/content/200/16922)
  - مسند أحمد 3251 — حديث ابن عباس رضي الله عنهما: «فبات عليّ على فراش النبي ﷺ تلك الليلة…»؛ والحاكم في المستدرك («شرى عليّ نفسه… ثم نام مكانه»، وصحّح إسناده) (https://shamela.ws/book/13606/119)
  - السنن الكبرى للبيهقي 6/289 — أقام عليّ ثلاث ليال وأيامها حتى أدّى عن رسول الله ﷺ الودائع التي كانت عنده للناس؛ قوّاه ابن حجر (التلخيص 3/112) وحسّنه الألباني (إرواء الغليل 1546) (https://saadalkhathlan.com/radio-programs/lessons/953)
  - Qur'an 4:58 (first part) (https://quran.com/4/58)

**نقاط تحتاج نظر المراجع:**

- هذه القصة من كتب السيرة (ابن إسحاق/ابن هشام، أحمد، الحاكم، البيهقي) لا من الصحيحين — يرجى تأكيد الدرجة والألفاظ.
- لم تُذكر نيّة القتل صراحةً؛ قيل «أرادوا أن يؤذوه». ولم تُتلَ 8:30 لذكرها القتل.
- «فعرفوا أنّ النبيّ ﷺ قد خرج، وردّ الله كيدهم» — من معنى رواية أحمد عن ابن عباس.
- تُعرض وتُتلى من 4:58 الكلمات 1–8 فقط «إنّ الله يأمركم أن تؤدّوا الأمانات إلى أهلها» مع شرح مبسّط.
- «كانت الودائع لأهل مكة» — من قول ابن إسحاق: «ليس بمكة أحد عنده شيء يخشى عليه إلا وضعه عنده».
- ملاحظة البيانات (`_note`): Sira reports (Ibn Ishaq; Ahmad/Hakim; Bayhaqi — hasan) rather than Bukhari/Muslim: reviewer please confirm the wording. The plotters' intention is told only as 'wanted to harm him'. 8:30 (about that night) is not played because it mentions killing; 4:58 words 1–8 («إن الله يأمركم أن تؤدوا الأمانات إلى أهلها») are played with a simple meaning.

**الحوار كاملًا:**

| # | المتكلّم | النص | English | النوع |
|---|---|---|---|---|
| 1 | الجدّة آمنة | أهلًا يا حبيبي! لو أعطاك صديقك لعبته وقال: احفظها لي حتى أرجع… ماذا تفعل؟ | Hello, my darling! If your friend gave you his toy and said, “Keep it safe for me until I come back”… what would you do? | سطر |
| 2 | الجدّة آمنة | هل تحفظها وتردّها إليه؟ | Would you keep it safe and give it back? | سؤال |
| 3 | الطفل | نعم، أحفظها وأردّها كما هي! | Yes — I'd keep it safe and give it back just as it was! | الطفل |
| 4 | الجدّة آمنة | ↳ أحسنت! هذه هي «الأمانة». وقصتنا اليوم عن النبيّ ﷺ وعن ابن عمّه عليّ بن أبي طالب رضي الله عنه. | Well done! That is “amanah” — keeping a trust. Our story today is about the Prophet ﷺ and his cousin, Ali ibn Abi Talib, may Allah be pleased with him. | ردّ |
| 5 | الطفل | أحتفظ بها لنفسي؟ | Keep it for myself? | الطفل |
| 6 | الجدّة آمنة | ↳ لا يا حبيبي! نردّها إلى صاحبها، وهذه هي «الأمانة». اسمع القصة. | No, my darling! We give it back to its owner — that is “amanah”. Listen to the story. | ردّ |
| 7 | الطفل | مَن هو عليّ بن أبي طالب؟ | Who was Ali ibn Abi Talib? | الطفل |
| 8 | الجدّة آمنة | ↳ هو ابنُ عمّ النبيّ ﷺ. عاش في بيته وهو صغير، وكان أوّلَ مَن آمن به من الصبيان، وصار بعد ذلك رابعَ الخلفاء الراشدين. | He was the Prophet's ﷺ cousin. He grew up in the Prophet's home as a boy, was the first boy to believe in him, and later became the fourth of the rightly guided caliphs. | ردّ |
| 9 | الطفل | وماذا كان يلقّب أهلُ مكة النبيَّ ﷺ؟ | What did the people of Makkah call the Prophet ﷺ? | الطفل |
| 10 | الجدّة آمنة | ↳ كانوا يسمّونه «الأمين»، لأنّه لا يخون أبدًا. حتى إنّ الناس كانوا يتركون عنده أشياءهم الثمينة ليحفظها لهم — وهي «الودائع». | They called him “al-Amin” — the Trustworthy — because he never broke a trust. People even left their precious things with him to keep safe; these were called “wada’i’”, deposits. | ردّ |
| 11 | الطفل | وماذا حدث ليلةَ الهجرة؟ | What happened on the night of the Hijra? | الطفل |
| 12 | الجدّة آمنة | ↳ أراد بعضُ كفّار مكة أن يؤذوا النبيَّ ﷺ، فأذِن الله له أن يهاجر إلى المدينة. وفي تلك الليلة قال النبيّ ﷺ لعليّ: «نَمْ على فراشي، وتَسَجَّ بِبُردي هذا». | Some of the disbelievers of Makkah wanted to harm the Prophet ﷺ, so Allah allowed him to emigrate to Madinah. That night the Prophet ﷺ said to Ali: “Sleep in my bed, and cover yourself with this cloak of mine.” | ردّ 🖼 `night_house` |
| 13 | الجدّة آمنة | ↳ يعني: نَمْ في مكاني، وتغطَّ بعباءتي الخضراء. وطمأنه أنّه لن يصيبه منهم شيءٌ يكرهه. | Meaning: sleep in my place and wrap yourself in my green cloak. And he reassured him that nothing bad would reach him from them. | ردّ 🖼 `green_cloak` |
| 14 | الطفل | ألم يخف عليّ؟ | Wasn't Ali afraid? | الطفل |
| 15 | الجدّة آمنة | ↳ كان عليٌّ رضي الله عنه شجاعًا، يحبّ النبيَّ ﷺ ويثق بكلامه. فنام في فراشه مطمئنًّا، وخرج النبيّ ﷺ سالمًا، وحفظه الله. | Ali was brave. He loved the Prophet ﷺ and trusted his word, so he slept in his bed calmly — and the Prophet ﷺ left safely, protected by Allah. | ردّ 🖼 `green_cloak` |
| 16 | الجدّة آمنة | ↳ وفي الصباح وجدوا عليًّا في الفراش، فعرفوا أنّ النبيّ ﷺ قد خرج، وردّ الله كيدهم. | In the morning they found Ali in the bed, and knew the Prophet ﷺ had already gone — Allah had spoiled their plan. | ردّ 🖼 `green_cloak` |
| 17 | الجدّة آمنة | لماذا نام عليٌّ في فراش النبيّ ﷺ؟ | Why did Ali sleep in the Prophet's ﷺ bed? | اختبار |
| 18 | الطفل | ✓ لأنّ النبيّ ﷺ طلب منه ذلك ليخرج بأمان | Because the Prophet ﷺ asked him to, so he could leave safely | خيار |
| 19 | الطفل | ✗ لأنّ فراشه كان أنعم | Because the bed was softer | خيار |
| 20 | الطفل | ✗ لأنّه كان متعبًا | Because he was tired | خيار |
| 21 | الجدّة آمنة | تلميح: تذكّر: ماذا قال النبيّ ﷺ لعليّ تلك الليلة؟ | Remember what the Prophet ﷺ told Ali that night… | تلميح |
| 22 | الجدّة آمنة | ثناء: أحسنت! أطاع عليٌّ النبيَّ ﷺ بشجاعةٍ وحبّ. | Well done! Ali obeyed the Prophet ﷺ with courage and love. | ثناء |
| 23 | الطفل | وماذا حدث للودائع التي عند النبيّ ﷺ؟ | What happened to the deposits the Prophet ﷺ was keeping? | الطفل |
| 24 | الجدّة آمنة | ↳ هنا الجزء الجميل! بقي عليٌّ في مكة بعد النبيّ ﷺ ثلاثَ ليالٍ وأيامَها، يردّ الودائع إلى أصحابها. | Here's the beautiful part! Ali stayed in Makkah for three nights and days after the Prophet ﷺ left, giving the deposits back to their owners. | ردّ 🖼 `trusts` |
| 25 | الجدّة آمنة | ↳ فلمّا أدّى الأماناتِ كلَّها إلى أهلها، هاجر ولحق بالنبيّ ﷺ في المدينة. | When every trust had been returned to its owner, he emigrated too and joined the Prophet ﷺ in Madinah. | ردّ 🖼 `trusts` |
| 26 | الطفل | حتى الذين آذَوه؟ ردّ إليهم أشياءهم؟ | Even to the people who hurt him? He gave their things back? | الطفل |
| 27 | الجدّة آمنة | ↳ نعم يا حبيبي! كانت الودائع لأهل مكة، والأمانة تُردّ إلى صاحبها دائمًا. هكذا علّمنا النبيّ ﷺ، حتى في أصعب الأوقات. | Yes, my darling! The deposits belonged to the people of Makkah, and a trust is always returned to its owner. That is what the Prophet ﷺ taught us — even in the hardest times. | ردّ |
| 28 | الجدّة آمنة | وقد أمرنا الله بذلك في القرآن. تعالَ نسمع أوّل الآية بصوت الشيخ. | Allah commands us to do this in the Quran. Come, let's hear the beginning of the verse in the sheikh's voice. | سطر |
| 29 | — | [تلاوة 4:58–4:58، الكلمات 1–8] شرح مبسّط: إنّ الله يأمركم أن تردّوا كلَّ ما اؤتُمنتم عليه إلى أصحابه كاملًا. | Allah commands you to give back everything you were trusted with to its owners, in full. | آيات |
| 30 | الجدّة آمنة | فماذا نتعلّم من قصة عليّ رضي الله عنه؟ | So what do we learn from the story of Ali? | اختبار |
| 31 | الطفل | ✓ أن أحفظ الأمانة وأردّها إلى صاحبها، وأكون شجاعًا في الخير | To keep a trust and return it to its owner — and to be brave in doing good | خيار |
| 32 | الطفل | ✗ أن آخذ ما ليس لي | To take what isn't mine | خيار |
| 33 | الطفل | ✗ أن أنسى ما أعطاني الناس لأحفظه | To forget what people gave me to keep | خيار |
| 34 | الجدّة آمنة | تلميح: تذكّر: ماذا فعل عليٌّ بالودائع قبل أن يهاجر؟ | Remember what Ali did with the deposits before he emigrated… | تلميح |
| 35 | الجدّة آمنة | ثناء: ممتاز! وكن «أمينًا» مثل نبيّنا ﷺ. | Excellent! And be “amin”, trustworthy, like our Prophet ﷺ. | ثناء |
| 36 | الطفل | سأحفظ الأمانة وأردّها دائمًا! | I'll always keep a trust and give it back! | سطر |
| 37 | — | [مكافأة 50 نقطة] تعلّمت قصة عليّ بن أبي طالب وليلة الهجرة والأمانات. | You learned the story of Ali ibn Abi Talib, the night of the Hijra and the trusts. | مكافأة |


---

# مواضع الرواة المستخدمة (Positions used)

كل موضع جديد على أرضٍ مفتوحة ويبعد ≥ 3 م عن أيّ راوٍ آخر (فُحص آليًا مقابل مصادمات القرية والترعة والماء والميل). موقف اللاعب = أمام المضيف بمسافة `stage.distance`.

| القصة | الشخصية | الموضع (x, z) | facing | المكان | ملاحظة |
|---|---|---|---|---|---|
| `abu-bakr-the-cave` | العمّ حمدان | (156.0, -120.0) | 0.0 | على الطريق قبل الدار القديمة، شمال صفّ الأعمدة |  |
| `umar-and-the-widow` | العمّ حمدان | (12.0, -4.2) | 0.8 | السوق، شمال شرق دكّان القرية (9, −7) |  |
| `umar-and-the-widow` | الجدّة آمنة | (13.8, -6.4) | 0.0 | السوق، شمال شرق دكّان القرية (9, −7) |  |
| `uthman-and-the-well` | الجدّ سالم | (-5.0, 7.2) | 0.0 | ساحة القرية، شمال البئر (−5, 4) |  |
| `ali-and-the-trusts` | الجدّة آمنة | (-26.7, -15.8) | 1.5708 | أمام باب بيت غرب الساحة (house_a عند −30.5, −16.9) |  |
| `nuh-and-the-ark` | الجدّ سالم | (10.0, 62.0) | 3.1416 | حقول الشاطئ الجنوبي للنهر، شرق الطريق الشمالي |  |
| `nuh-and-the-ark` | العمّ حمدان | (7.5, 62.8) | 2.5 | حقول الشاطئ الجنوبي للنهر، شرق الطريق الشمالي |  |
| `ibrahim-and-the-fire` | العمّ حمدان | (141.0, -50.0) | -0.6 | الغيطان الشرقية على طريق الدار القديمة |  |
| `ibrahim-and-the-fire` | الجدّ سالم | (143.0, -51.2) | -0.82 | الغيطان الشرقية على طريق الدار القديمة |  |
| `musa-on-the-river` | الجدّة آمنة | (-41.8, 32.0) | 1.5708 | الضفة الشرقية للترعة الحقلية x = −45 |  |
| `isa-in-the-cradle` | الجدّة زينب | (-93.0, -8.1) | 0.0 | مقعد العريشة في الواحة (−92, −9) | جالسة على مقعد ارتفاعه ≈0.30 م — افحص بصريًا |
| `muhammad-the-trustworthy` | الجدّ سالم | (5.0, 125.0) | 3.1416 | سفح التلال شمال النهر، شرق الطريق الشمالي |  |
| `muhammad-the-trustworthy` | الجدّة آمنة | (7.6, 125.6) | -2.41 | سفح التلال شمال النهر، شرق الطريق الشمالي |  |
| `ali-and-the-trusts` | دعامة lantern | (-27.95, -17.3) | 1.5708 | | |
| `musa-on-the-river` | دعامة basket | (-41.9, 33.4) | 0.4 | | |

نموذج الجدّة زينب (`grandma_zainab.glb`) فيه حركتا `sit` و`sit_talk` فقط، والمصطبة الوحيدة مشغولة بقصة أصحاب الفيل؛ لذا تجلس في قصة عيسى على مقعد عريشة الواحة. إن لم يبدُ الجلوس جيدًا فالبديل: الجدّة آمنة واقفةً في الموضع نفسه.


---

# مفاتيح الصور الجديدة (to paint)

مفاتيح `scene` جديدة لم تُرسم بعد (تختفي الصورة بهدوء حتى تُضاف إلى `src/game/ui/scenes.js` و`public/illustrations/`). كلها أماكن وأشياء وحيوانات — بلا أنبياء ولا صحابة ولا أشخاص. المفاتيح المعاد استخدامها: `year`، `kaaba`، `night_house`.

| المفتاح | القصة | موجز الرسم |
|---|---|---|
| `hijra_road` | أبو بكر | Desert track at dawn leading out of a mountain valley: two saddled camels resting beside a small leather food bag tied with a strip of cloth; long shadows. No riders, no people. |
| `cave_thawr` | أبو بكر | Night: a small, low cave mouth in a rocky mountainside, starry sky, soft moonlight; faint sheep silhouettes grazing far below. Nobody in or near the cave. |
| `food_camel` | عمر | An old Madinah market lane in the morning: a strong camel by a mud-brick yard, loaded with two big grain sacks and cloth bundles between them; its rope hanging free. No people. |
| `well_rumah` | عثمان | A stone-rimmed desert well among palm trees, several leather buckets on ropes round the rim, clear water glinting inside; warm afternoon light. No people. |
| `seven_ears` | عثمان | Close-up of one wheat stalk with seven golden ears rising from a single grain in dark soil; a Nile-village field softly blurred behind; sun rays. |
| `green_cloak` | عليّ | Moonlit simple room: a low mattress with a green Hadrami cloak laid over it, a small clay lamp, a window with stars. No person visible. |
| `trusts` | عليّ | Daylight room: an open wooden chest, small cloth-wrapped bundles, a few coins and folded fabric set out neatly as if being handed back; doorway to a bright street. No people. |
| `ark_build` | نوح | A large wooden ship half-built on dry land under a clear sky: timber ribs, stacked planks, a mallet and a basket of nails; distant hills. No people. |
| `ark_sea` | نوح | The finished ark riding big but rounded, non-threatening waves in grey rain with light breaking through; pairs of animal silhouettes on deck. No people, no drowning. |
| `ark_judi` | نوح | The ark resting on a green mountain top as the water recedes; fresh sunlight, wet grass, birds in the sky (no dove-with-branch, no rainbow). No people. |
| `idols_broken` | إبراهيم | A dim ancient temple hall: faceless carved stone statues broken into pieces on the floor, one large faceless statue left standing; a shaft of light from the doorway. Stylised, not scary. No people. |
| `cool_fire` | إبراهيم | A ring of large flames turning soft and blue-white at the centre, where green grass and small flowers grow; calm, peaceful glow. No person shown. |
| `nile_basket` | موسى | The Nile at dawn among papyrus reeds: a small sealed reed box/basket floating on calm water, lotus flowers, a heron. No people. |
| `palace_nile` | موسى | An ancient Egyptian palace with columns and gardens on the Nile bank, steps down to the water; evening light. No people. |
| `palm_stream` | عيسى | A single tall date palm heavy with ripe red-gold dates, a small clear stream at its foot, a few dates fallen on the sand; soft dawn light. No people. |
| `hira_cave` | محمد ﷺ | Night: a small cave near the top of a rocky mountain (Jabal al-Nour) looking over a sleeping valley with a few lights; crescent moon and stars. Nobody depicted. |
