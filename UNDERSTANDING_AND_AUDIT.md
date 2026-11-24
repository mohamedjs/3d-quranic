# ملخص الفهم ومراجعة المشروع — رحلة مع القرآن (`3d-quranic`)

> **تنبيه حالة العمل:** هذا الملف يوثّق ما تم فهمه ومراجعته في المشروع قبل البدء بأي تعديل فعلي. **لم يتم تعديل أي ملف كود أو نموذج Blender أو تشغيل تثبيت أو بناء حتى الآن**، والعمل متوقف حاليًا بانتظار موافقتك وتوجيهك للخطوة القادمة.

---

## 1. فهم المشروع الحالي والبنية التقنية (Project Understanding)

- **اسم اللعبة وفكرتها:** «رحلة مع القرآن» (`Quran Journey`) — لعبة استكشاف ثلاثية الأبعاد للأطفال في قرية ريفية دافئة وقت الغروب، يتجول فيها الطفل ليلتقي بأهل القرية، ويستمع إلى القصص القرآنية والنبوية وقصص الصحابة عبر حوار تفاعلي ورسومات توضيحية، ثم يستمع لتلاوة الآيات من **Quran.com API v4** مع التفسير الميسّر والمعاني.
- **المكدس التقني (Stack):**
  - الواجهة والرسومات ثلاثية الأبعاد: `React 19` + `React Three Fiber 9` + `drei 10` + `Three.js r186` (`WebGL 2` + GLSL shaders) + `Vite 8` (في [package.json](file:///var/www/html/old/3d-quranic/package.json) و[vite.config.js](file:///var/www/html/old/3d-quranic/vite.config.js)).
  - نسخة الويب والعمل بدون إنترنت (PWA): [src/pwa/sw.js](file:///var/www/html/old/3d-quranic/src/pwa/sw.js) + [src/pwa/pwa.js](file:///var/www/html/old/3d-quranic/src/pwa/pwa.js) + [tools/vite-pwa.js](file:///var/www/html/old/3d-quranic/tools/vite-pwa.js) + [public/manifest.webmanifest](file:///var/www/html/old/3d-quranic/public/manifest.webmanifest).
  - نسخة الأندرويد: `Capacitor 8` في مجلد `android/` (`com.mohamedjs.rehla`).
  - النشر الحالي: Railway (`rehla-ma3-alquran.up.railway.app`) كرابط رئيسي، و**GitHub Pages** (`https://mohamedjs.github.io/3d-quranic/`) عبر [build.yml](file:///var/www/html/old/3d-quranic/.github/workflows/build.yml) مع إعداد `base: './'` في [vite.config.js](file:///var/www/html/old/3d-quranic/vite.config.js).
- **المحتوى الحالي:**
  - `18` قصة في [encounters.json](file:///var/www/html/old/3d-quranic/public/data/encounters.json) موزعة على `3` أقسام (`quran`: 9 قصص، `prophets`: 5 قصص، `companions`: 4 قصص) وبـ `3` لغات (`ar`, `en`, `ru`).
  - النصوص القرآنية والتلاوات تُجلب لحظيًا عبر [quran.js](file:///var/www/html/old/3d-quranic/src/game/systems/quran.js)، والأصوات التمثيلية المسجلة مخزنة في `public/audio/`.
- **منظومة الأداء والجودة ([quality.js](file:///var/www/html/old/3d-quranic/src/game/systems/quality.js) و[store.js](file:///var/www/html/old/3d-quranic/src/game/systems/store.js)):**
  - توجد `5` مستويات (`lite`, `low`, `medium`, `high`, `ultra`)، وتبدأ اللعبة افتراضيًا بمستوى **Lite (`خفيف جدًا`)** (سقف 30 إطار/ثانية، دقة شبكة أرضية `224²`، ظلال ثابتة مخبوزة للعالم + Blob Shadows للشخصيات عبر [Blobs.jsx](file:///var/www/html/old/3d-quranic/src/game/characters/Blobs.jsx)، ودمج للمباني والنباتات) لتعمل بسلاسة على الهواتف الضعيفة والمتصفح والأندرويد.
- **البيئة المحلية المتاحة على الجهاز (تم التحقق منها):**
  - `Blender 5.2.2 LTS` (يعمل بدون واجهة عبر `-b` مع `BLENDER_EEVEE` و`numpy 2.3.4`).
  - `Node v22.17.0` + `npm 11.4.2` + `Python 3.12.3`.
  - مجلد `node_modules/` غير مثبت حاليًا في مسار المشروع (يحتاج `npm ci` عند بدء التنفيذ).

---

## 2. مراجعة الشخصيات الحالية في Blender v2 وخطة إعادة التصميم (v3)

### ما تم رصده في Blender v2
بمراجعة صور المعاينة ([cast_lineup.png](file:///var/www/html/old/3d-quranic/blender/v2/previews/cast_lineup.png)، [cast_faces.png](file:///var/www/html/old/3d-quranic/blender/v2/previews/cast_faces.png)، [village_cast.png](file:///var/www/html/old/3d-quranic/blender/v2/previews/village_cast.png)) وسكريبتات [blender/v2/characters/](file:///var/www/html/old/3d-quranic/blender/v2/characters/build_all.py):
- **أحجام النماذج الحالية في `public/models/`:** `player.glb` (399 KB)، `farmer.glb` (336 KB)، `trader.glb` (331 KB)، `grandma.glb` (322 KB)، `grandma_zainab.glb` (272 KB).
- **الوجوه والملامح (`head.py`):** الوجه مبني على كرة أنمي حادة الذقن (مثلث مدبب) مع رسم العيون والأنف والفم كملصق ثنائي الأبعاد (`face` texture) دون أنف أو حواجب مجسّمة، مع تداخل خطوط الـ `outline` حول الوجه مما يعطي مظهرًا غير متناغم ومظلمًا عند الأطراف.
- **الهيكل والأجسام (`body.py` و`garments.py`):** الاعتماد على أجسام MPFB الواقعية بهيكل `game_engine` ثقيل (~68 عظمة تشمل عظام الأصابع الثلاثين) مع ملابس مقصوصة ومشدودة عليها بالـ shrinkwrap/lathe، مما يسبب:
  - تداخل/اختراق (Clipping) واضح في صدر ومرفقي الجدة زينب الجالسة والتنورة، وعند رقبة وشماغ العم حمدان، ولحية الجد سالم حول الفك.
  - شعر الولد (`curly_hair`) يظهر ككتل منفصلة، وحمّالات حقيبة الظهر غير منسابة بنعومة.
  - استهلاك مثلثات وعظام أعلى مما يحتاجه المتصفح والهواتف في وضع Lite.

### خطة إعادة التصميم المقترحة في Blender v3 (`blender/v3/characters/` ← `public/models/*.glb`)
مع الحفاظ على مجلد `blender/v2/` كما هو كمرجع تاريخي، سنبني منظومة نظيفة ومستقلة تمامًا لـ **v3** متوافقة 100% مع محرك اللعبة في [glbRig.js](file:///var/www/html/old/3d-quranic/src/game/characters/glbRig.js):
1. **أسلوب فني موحّد ودافئ (Storybook Stylized 3D — مزيج Pixar/Ghibli):**
   - نسب شخصيات لطيفة ودافئة (الطفل ~1:4.2، الكبار ~1:5.5)، ملامح مستديرة مريحة بدون ذقن مدبب حاد.
   - **رأس ثلاثي الأبعاد حقيقي (`head_v3.py`):** أنف لطيف مجسّم ثلاثي الأبعاد، أذنان مستديرتان (تُخفى تحت الحجاب/الغترة)، حواجب مجسّمة 3D متناسقة مع لون الشعر/اللحية، نسيج وجه 512px بعيون دافئة معبّرة، جفون منحنية (`lid_l`, `lid_r`) للرمش، وفم (`mouth`) ناعم للحوار.
   - **خطوط تحديد نظيفة وانتقائية (`outline`):** استثناء العيون والجفون والفم والحواجب والنظارة من الـ outline تمامًا، وتخفيف السُمك على الوجه واليدين (`0.0028 m`) مع إبقائه واضحًا على الملابس والشعر (`0.0048 m`).
2. **خفّة فائقة للويب والأندرويد:**
   - هيكل عظمي خفيف من **22 عظمة فقط** (بدل ~68 عظمة في MPFB) مع أوزان وزن تحليلية ناعمة بلا تشوهات `DATA_TRANSFER`.
   - ميزانية مستهدفة: `4,500–8,500` مثلثًا شاملة الـ outline، وحجم ملف **`90–260 KB`** لكل GLB (بعد ضغط Draco level 6)، و`2–3` Draw Calls فقط للشخصية في وضع Lite.
3. **إعادة تصميم الشخصيات الـ 5 الحالية + إضافة شخصيتين جديدتين (الإجمالي 7 شخصيات):**
   - `player.glb` (1.25 م — `idle`, `walk`, `run`, `talk`): الولد المستكشف بشعر مموج متدرج وغرة ناعمة، جلابية كريمي مطرزة عند الصدر بالتركواز والذهبي، حزام قماشي، سروال مريح، وحقيبة ظهر جلدية متقنة بلا طفو.
   - `farmer.glb` (1.74 م — `idle`, `walk`, `talk`): الجدّ سالم بعمامة ريفية متعددة الطيات، لحية وشارب أبيضين متناسقين مع الفك، جلابية بنية فوقها صديري زيتي وشال كتف، وعصا خشبية مصقولة في اليد اليسرى.
   - `grandma_zainab.glb` (1.58 م — `sit`, `sit_talk`): الجدة زينب الجالسة على المصطبة بطرحة داكنة مزينة بحافة ذهبية، فستان مريح منسدل فوق الركبتين بتصميم مخصوص للجلوس بدون أي تداخل مع الصدر أو الذراعين.
   - `grandma.glb` (1.60 م — `idle`, `walk`, `talk`): الجدة آمنة بطرحة نيلية منسدلة، نظارة ذهبية دائرية متمركزة بدقة على جسر الأنف، وفستان زمردي مطرز.
   - `trader.glb` (1.78 م — `idle`, `walk`, `talk`): العم حمدان بشماغ أحمر وأبيض منسدل بنعومة دون اختراق الرقبة مع عقال أسود وذهبي، ثوب أزرق ملكي وبشت قوافل مفتوح بحواف ذهبية.
   - `sheikh.glb` *(جديد)* (1.76 م — `idle`, `walk`, `talk`): **الشيخ يونس** (معلم القرية) بعمامة بيضاء فوق طربوش عنابي خفيف، لحية مشذبة، وقفطان زيتي فاتح فوق ثوب عاجي.
   - `aunt.glb` *(جديد)* (1.58 م — `idle`, `walk`, `talk`): **الخالة سلمى** (راعية البساتين) بطرحة وردي-تراكوتا دافئة وفستان مغرة ذهبي مع حزام تركواز مطرز.
4. **حركات سلسة ومتقنة (`anim_v3.py`):** حلقات حركة مغلقة تمامًا (`24 fps`) متوافقة مع سرعة المشي (`~1.1 m/cycle`) والجري (`~2.7 m/s`) لمنع انزلاق القدمين، مع حركات يد معبرة أثناء الحديث ومزامنة الرمش والفم.

---

## 3. الأخطاء والمشاكل المكتشفة في الكود الحالي (Code & World Audit)

### أ. أخطاء رسمة الطريق والجسور والمسار الإرشادي
1. **تكسّر الطرق وتقطّعها في وضع Lite (`terrainMaterial.js` + `terrainGeometry.js`):**
   - في [terrainGeometry.js](file:///var/www/html/old/3d-quranic/src/game/terrain/terrainGeometry.js) تُحسب مسافة الطريق `vMask.y` عند رؤوس الشبكة (Vertices) فقط؛ وعلى شبكة وضع Lite (`224²` على مساحة `520 م` ≈ `2.32 م` بين كل نقطة)، تظهر الطرق القطرية والضواحي متعرجة أو متقطعة في [terrainMaterial.js](file:///var/www/html/old/3d-quranic/src/game/shaders/terrainMaterial.js).
   - **الإصلاح:** تصدير `PATHS` من [heightfield.js](file:///var/www/html/old/3d-quranic/src/game/terrain/heightfield.js) وحساب `pathDist` **لكل بكسل داخل الـ Fragment Shader** (Per-Pixel) لإظهار طرق ناعمة متصلة بحواف ترابية طبيعية على جميع مستويات الجودة، مع إضافة مسارات فرعية تربط ساحة القرية والمصطبة والواحة والحقول والآثار والتلال.
2. **جسر مشاة مفقود من نظام المشي والملاحة (`details.js` vs `heightfield.js`):**
   - يوجد جسر مشاة مرسوم عند الترعة `(-15, 34.5)` في [details.js](file:///var/www/html/old/3d-quranic/src/game/world/details.js#L24)، لكنه **غير مسجل في `FOOTBRIDGES`** داخل [heightfield.js](file:///var/www/html/old/3d-quranic/src/game/terrain/heightfield.js#L84)، وبالتالي يسقط اللاعب في الماء لو عبره ولا يستخدمه مسار A*! كما تفتقر قنوات الري في الحقول (`CANALS = [-45, -15, 15, 45]`) لجسور عبور كافية.
   - **الإصلاح:** توحيد جميع الجسور في `FOOTBRIDGES` (بما فيها `(-15, 34.5)` + `4` جسور إضافية على قنوات الحقول) وإزالة السطر المكرر من `details.js`.
3. **عيوب الأسهم الإرشادية الذهبية 3D (`guide.js`):**
   - الأسهم الأرضية في [guide.js](file:///var/www/html/old/3d-quranic/src/game/systems/guide.js#L330) تدور حول المحور الرأسي فقط (`_up`) وتبقى أفقية، فتغوص داخل الأرض على المنحدرات والتلال والجسور.
   - المسارات القصيرة (`< 4 م`) تختفي تمامًا بسبب معادلة الإخفاء في [guide.js](file:///var/www/html/old/3d-quranic/src/game/systems/guide.js#L329).
   - تنعيم Chaikin في `buildRoute()` لا يتحقق من قابلية المشي (`grid.walkable`) فقد يمر المسار بزاوية مبنى أو ماء، وإعادة بناء المسار تعيد المؤشر `prog = 0`.
4. **انزياح مسار الخريطة العالمية عند التكبير والتحريك (`ui.js`):**
   - في [ui.js](file:///var/www/html/old/3d-quranic/src/game/ui/ui.js#L330-L331)، طبقة الخريطة `layer` تُحرك بوحدة `%` بينما عنصر المسار `routeG` خارجها ويُحرك بوحدة `px`! عند عمل Zoom/Pan في خريطة العالم ينفصل الخط الذهبي عن الطرق والشخصيات.

### ب. أخطاء تحميل النقط / العملات الخاصة بكل قصة (`coins.js` + `game.js`)
1. **تأخر ظهور العملات وبقاء عداد القفل `…`:**
   - يعتمد [coins.js](file:///var/www/html/old/3d-quranic/src/game/world/coins.js#L291-L312) على طابور بحث زمني (3–6 مللي ثانية/إطار)، وعند اختيار قصة من القائمة أو الخريطة قد تظهر رسالة `نجهّز العملات على الطريق…` أو `…` بدل العملات الفعلية حتى يفرغ الطابور. **الإصلاح:** إضافة دالة `ensure(id)` تُنهي تجهيز مجموعة القصة النشطة فورًا عند اختيارها.
2. **اختفاء عملات من القصة الجديدة عند التبديل السريع (`POP` slot bug):**
   - في [coins.js](file:///var/www/html/old/3d-quranic/src/game/world/coins.js#L326-L330)، الخانات التي ما زالت في حالة التلاشي `ST[i] === POP` لا يتم تفريغها ولا الكتابة فوقها عند استدعاء `show(id)` لقصة أخرى، مما يسقط بعض عملات القصة الجديدة. **الإصلاح:** فصل أنيميشن التلاشي في مصفوفة `pops` مستقلة.
3. **حفظ مسارات فاشلة أو قديمة في `localStorage`:**
   - مفتاح الكاش في [coins.js](file:///var/www/html/old/3d-quranic/src/game/world/coins.js#L195-L310) لا يتضمن بصمة إحداثيات القصص، ويقوم بحفظ المسار حتى لو كان `reached === false`.
4. **وضوح مواقع النقط على الخريطة:**
   - إضافة `activeCoords(id)` لعرض نقاط العملات غير المجمّعة للقصة المستهدفة على الخريطة المصغرة وخريطة العالم، مع ضمان وجود قوس ترحيبي من العملات على الاقتراب الأخير لأي قصة يختارها الطفل.

### ج. أخطاء القصص والرسومات والواجهة والأداء
1. **تداخل قصتين في الواحة (`encounters.json`):**
   - قصتا `yusuf-dream` (`[-89.5, -7.5]`) و`isa-in-the-cradle` (`[-93.0, -8.1]`) المسافة بينهما **`3.55 م`** فقط (أقل من `talkRadius` الافتراضي `3.4–3.6 م`) مما يسبب تداخل أزرار الحوار والفقاعات.
2. **نقص الرسومات التوضيحية للقصص (`scenes.js`):**
   - في `public/illustrations/` توجد `19` صورة `.webp` تغطي `Title` وقصص السور الأولى/أسباب النزول، بينما هناك **`16` مشهدًا** في قصص الأنبياء والصحابة الحالية ليس لها صورة `.webp` ولا بديل SVG في [scenes.js](file:///var/www/html/old/3d-quranic/src/game/ui/scenes.js) (`cave_thawr`, `hijra_road`, `food_camel`, `seven_ears`, `well_rumah`, `green_cloak`, `trusts`, `ark_build`, `ark_judi`, `ark_sea`, `cool_fire`, `idols_broken`, `nile_basket`, `palace_nile`, `palm_stream`, `hira_cave`) فتظهر شاشة فارغة أثناء الحوار.
3. **نقص بيانات الواجهة (`ui.js` و`ornaments.svg`):**
   - جدول `SURAHS` في [ui.js](file:///var/www/html/old/3d-quranic/src/game/ui/ui.js#L111) يحتوي على `5` سور فقط (`2, 12, 59, 105, 106`) فتظهر بقية السور في بطاقات القصص كأرقام مجردة بدون أسماء السور!
   - كائن `REGIONS` ([ui.js](file:///var/www/html/old/3d-quranic/src/game/ui/ui.js#L31-L38)) يفتقد الترجمة الروسية `ru`.
   - الصور الشخصية `PORTRAITS` في [ornaments.svg](file:///var/www/html/old/3d-quranic/public/ui/ornaments.svg) و[ui.js](file:///var/www/html/old/3d-quranic/src/game/ui/ui.js#L21-L25) تقتصر على 3 وجوه (`grandma`, `farmer`, `player`) بدون صور مميزة للعم حمدان والجدة آمنة أو الشخصيات الجديدة.
4. **سقف الظلال في وضع Lite ومرونة محمّل النماذج:**
   - [Blobs.jsx](file:///var/www/html/old/3d-quranic/src/game/characters/Blobs.jsx#L12) يحدد `MAX = 24` مما يقطع الظلال مع زيادة عدد الشخصيات.
   - [glbRig.js](file:///var/www/html/old/3d-quranic/src/game/characters/glbRig.js#L17) يشترط `content-type` محددًا في طلب `HEAD` (أمر قد يسبب حساسية مع بعض خوادم الاستضافة)، ودالة `wave()` فيه فارغة.

---

## 4. تجهيز نسخة الويب و GitHub Pages والأداء الخفيف

- مسار النشر إلى GitHub Pages مهيأ في [build.yml](file:///var/www/html/old/3d-quranic/.github/workflows/build.yml) مع `base: './'` في [vite.config.js](file:///var/www/html/old/3d-quranic/vite.config.js) وService Worker نسبي المسارات.
- التحسينات المخططة للويب وGitHub Pages والأندرويد:
  - إضافة ملف `public/.nojekyll` لمنع Jekyll على GitHub Pages من تجاهل أو تعطيل أي ملفات.
  - جعل فحص `HEAD` في [glbRig.js](file:///var/www/html/old/3d-quranic/src/game/characters/glbRig.js) مرنًا بحيث يرفض فقط صفحات `text/html` (أي أخطاء 404 مقنّعة).
  - تحسين تدرج الـ Cel Shading في [toon.js](file:///var/www/html/old/3d-quranic/src/game/shaders/toon.js) وإضاءة الـ Hemisphere في [Lighting.jsx](file:///var/www/html/old/3d-quranic/src/game/lighting/Lighting.jsx) وإضاءة خفيفة لملامح الوجه (`emissive` دافئ بسيط) **بدون أي تكلفة إضافية على كارت الشاشة أو الـ Draw Calls**.
  - التحقق بعد التعديل من `npm run build` وتقرير `dist/precache-report.json` وفحص اللعبة فعليًا في المتصفح على الخادم المحلي.

---

## 5. التوسع إلى 28 قصة (+10 قصص جديدة) وخطة التعاون مع كلود

### القصص العشر الجديدة المقترح إضافتها (بالعربية الفصحى والإنجليزية والروسية، مع حفظ قواعد عدم تجسيد الأنبياء والصحابة)
- **قصص الأنبياء (`prophets`):**
  1. `yunus-and-the-whale` — يونس عليه السلام والحوت (`21:87–21:88`)
  2. `sulayman-and-the-ant` — سليمان عليه السلام والنملة (`27:18–27:19`)
  3. `dawud-and-the-birds` — داود عليه السلام وتسبيح الجبال والطير (`34:10–34:11`)
  4. `ayyub-patience` — صبر أيوب عليه السلام (`21:83–21:84`)
- **قصص من القرآن (`quran`):**
  5. `companions-of-the-cave` — أصحاب الكهف (`18:10–18:12`)
  6. `luqman-wisdom` — نصائح لقمان لابنه (`31:17–31:19`)
  7. `owners-of-the-garden` — أصحاب الجنة والعطاء (`68:17–68:20`)
- **قصص الصحابة (`companions`):**
  8. `bilal-the-muezzin` — بلال بن رباح رضي الله عنه (`49:13`)
  9. `khadijah-the-supportive` — خديجة بنت خويلد رضي الله عنها (`93:6–93:8`)
  10. `salman-the-seeker` — سلمان الفارسي رضي الله عنه ورحلة البحث عن الحق (`29:69`)
- بالإضافة إلى رسم **`36` مشهد SVG توضيحي** (`16` مفقودة حاليًا + `20` للقصص الجديدة) وإنشاء أداة فحص آلي `tools/verify_world.mjs` تتأكد من عدم تداخل أي شخصية أو مبنى أو ماء، ووصول مسار A* لكل القصص، وتوليد `>= 20` عملة قابلة للجمع لكل قصة.

### تقسيم العمل بيننا وبين كلود في المراحل القادمة
| المسؤول | المهام الأساسية | المخرجات |
|---|---|---|
| **دورنا (Blender + المحرك والرسومات + GitHub Pages)** | 1. تصميم وبناء الشخصيات السبع في **Blender v3** وتصديرها `.glb` مع المعاينات.<br>2. إصلاح شادر الطرق، الجسور، الأسهم المائلة، خريطة العالم، ونظام العملات.<br>3. إضافة القصص الـ 10 الأولية + الـ 36 رسمة + `tools/verify_world.mjs` + تجهيز الويب لـ GitHub Pages.<br>4. كتابة الدليل النهائي الكامل للتعاون (`PROJECT_REPORT_AND_COLLAB_GUIDE.md`). | `blender/v3/characters/*.py`<br>`public/models/*.glb`<br>`src/game/...`<br>`tools/verify_world.mjs` |
| **دور كلود بعدنا (توسيع القصص والصوتيات والنمو)** | 1. إضافة عشرات القصص الجديدة في `public/data/encounters.json` باستخدام الشخصيات الـ 7 الجاهزة وقالب القصص المعتمد.<br>2. توليد الملفات الصوتية للقصص الجديدة عبر `tools/voice_v2/` وتحديث `public/audio/manifest.json`.<br>3. تشغيل `node tools/verify_world.mjs` و`npm run build` قبل كل رفع لضمان خلو العالم والنسخة من أي أخطاء. | قصص جديدة + أصوات عربية/إنجليزية/روسية + مراجعة شرعية ولغوية |

---

## 6. الخطوة التالية
- العمل متوقف الآن بناءً على طلبك.
- فور تأكيدك (أو إخباري بأي تعديل تحب إضافته على التصميم أو القصص أو الشخصيات)، سأبدأ فورًا بتنفيذ الخطة من **Blender v3** حتى **تجهيز الويب على GitHub Pages** والتقرير النهائي.
