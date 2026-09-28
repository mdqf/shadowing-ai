// src/data/l1Feedback.ts
export interface L1Tip {
  phoneme: string;
  title: string;
  persianMistake: string;
  correctionTip: string;
  example: string;
}

export const L1_PERSIAN_FEEDBACK: Record<string, L1Tip> = {
  "θ": {
    phoneme: "θ",
    title: "تلفظ صدای /θ/ (مثل Think)",
    persianMistake: "فارسی‌زبانان این صدا را معمولاً شبیه /s/ یا /t/ تلفظ می‌کنند.",
    correctionTip: "نوک زبان خود را بین دندان‌های بالا و پایین قرار دهید و هوا را بدون لرزش تارهای صوتی بیرون بفرستید.",
    example: "Think, Three, Thanksgiving",
  },
  "ð": {
    phoneme: "ð",
    title: "تلفظ صدای /ð/ (مثل This)",
    persianMistake: "فارسی‌زبانان این صدا را معمولاً شبیه /z/ یا /d/ تلفظ می‌کنند.",
    correctionTip: "نوک زبان را بین دندان‌ها قرار داده و همراه با لرزش تارهای صوتی (صداکننده) تلفظ کنید.",
    example: "This, That, Weather",
  },
  "w": {
    phoneme: "w",
    title: "تمایز صدای /w/ و /v/",
    persianMistake: "در زبان فارسی صدای /w/ وجود ندارد و معمولاً به جای آن /v/ تلفظ می‌شود.",
    correctionTip: "لب‌های خود را کاملاً گرد و غنچه کنید (شبیه به حالت فوت کردن) و بدون برخورد دندان به لب پایین آن را ادا کنید.",
    example: "Water, World, Very vs Every",
  },
  "ɪ": {
    phoneme: "ɪ",
    title: "تلفظ ای کوتاه /ɪ/ در برابر /iː/",
    persianMistake: "اشتباه گرفتن صدای کوتاه (Ship) با صدای کشیده (Sheep).",
    correctionTip: "این صدا بسار کوتاه و شبیه به «إ» خنثی تلفظ می‌شود و نباید آن را مانند «ای» کشیده فارسی ادا کرد.",
    example: "Bit vs Beat, Sit vs Seat",
  },
  "æ": {
    phoneme: "æ",
    title: "تلفظ صدای /æ/ (مثل Cat)",
    persianMistake: "ادا کردن آن شبیه به «أ» کوتاه فارسی یا /e/.",
    correctionTip: "دهان را گشادتر باز کنید و فک پایین را کمی بیشتر پایین بیاورید.",
    example: "Cat, Apple, Bad",
  },
};