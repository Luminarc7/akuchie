// Japanese for Commander Spellbook's combo text: results, required card
// kinds, prerequisites and steps. Card names arrive as «0», «1» … (the
// combo's cards) and «T0» … (its required card kinds); mana symbols stay as
// they are. Anything the rules below don't cover returns null, and the site
// shows that line in English.
const COMBO_JA = (() => {
  const NUM = { a: 1, an: 1, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12, both: 2, single: 1 };
  const num = w => { w = String(w || '').toLowerCase(); return NUM[w] !== undefined ? NUM[w] : (/^\d+$/.test(w) ? Number(w) : null); };
  const ORD = { first: '1つ目の', second: '2つ目の', third: '3つ目の', fourth: '4つ目の', fifth: '5つ目の', last: '最後の' };
  const TYPES = {
    Soldier: '兵士', Insect: '昆虫', Saproling: '苗木', Servo: '霊気装置', Zombie: 'ゾンビ', Spirit: 'スピリット', Goblin: 'ゴブリン', Elf: 'エルフ',
    Warrior: '戦士', Human: '人間', Thopter: '飛行機械', Squirrel: 'リス', Rat: 'ネズミ', Bird: '鳥', Cat: '猫', Dog: '犬', Wolf: '狼', Beast: 'ビースト',
    Elemental: 'エレメンタル', Plant: '植物', Eldrazi: 'エルドラージ', Spawn: '落とし子', Scion: '末裔', Germ: '細菌', Faerie: 'フェアリー', Dragon: 'ドラゴン',
    Knight: '騎士', Construct: '構築物', Golem: 'ゴーレム', Myr: 'マイア', Vampire: '吸血鬼', Wizard: 'ウィザード', Cleric: 'クレリック', Rogue: 'ならず者',
    Pirate: '海賊', Dinosaur: '恐竜', Merfolk: 'マーフォーク', Ape: '類人猿', Frog: 'カエル', Snake: '蛇', Ox: '雄牛', Horror: 'ホラー', Demon: 'デーモン',
    Angel: '天使', Treefolk: 'ツリーフォーク', Fungus: '菌類', Ooze: 'ウーズ', Hydra: 'ハイドラ', Kobold: 'コボルド', Thrull: 'スラル', Illusion: 'イリュージョン',
    Shapeshifter: '多相の戦士', Wall: '壁', Druid: 'ドルイド', Shaman: 'シャーマン', Ally: '同盟者', Egg: '卵', Sculpture: '彫像', Devil: 'デビル', Imp: 'インプ',
    Skeleton: 'スケルトン', Spider: '蜘蛛', Bat: 'コウモリ', Fish: '魚', Octopus: '蛸', Kraken: 'クラーケン', Monk: 'モンク', Citizen: '市民', Mercenary: '傭兵',
    Detective: '探偵', Robot: 'ロボット', Gnome: 'ノーム', Dwarf: 'ドワーフ', Hound: '猟犬', Boar: '猪', Elk: 'へラジカ', Bear: '熊', Phyrexian: 'ファイレクシアン',
    Mite: 'ダニ', Rhino: 'サイ', Camarid: 'カマリッド', Worm: 'ワーム', Wurm: 'ワーム', Avatar: 'アバター', Minion: 'ミニオン', Assassin: '暗殺者', Ninja: '忍者',
    Samurai: '侍', Minotaur: 'ミノタウルス', Centaur: 'ケンタウルス', Giant: '巨人', Troll: 'トロール', Ogre: 'オーガ', Satyr: 'サテュロス', Nymph: 'ニンフ', Dryad: 'ドライアド', Coward: '臆病者', Survivor: '生存者', Hero: '英雄', Mutant: 'ミュータント', Turtle: '亀', Halfling: 'ハーフリング', Orc: 'オーク', Army: '軍団',
  };
  const TOKENS = {
    Treasure: '宝物', Clue: '手掛かり', Food: '食物', Blood: '血', Gold: '金', Map: '地図', Powerstone: 'パワーストーン', Shard: '欠片', Junk: 'ジャンク',
    Lotus: '蓮', Incubator: '培養器', Fish: '魚', Rock: '岩', Munitions: '弾薬', Mutagen: 'ミュータジェン', Heartwood: '心材',
  };
  const KW = { flying: '飛行', haste: '速攻', defender: '防衛', lifelink: '絆魂', vigilance: '警戒', trample: 'トランプル', deathtouch: '接死',
    'first strike': '先制攻撃', reach: '到達', menace: '威迫', indestructible: '破壊不能', hexproof: '呪禁', persist: '頑強', undying: '不死' };
  const COUNTERS = { charge: '蓄積', loyalty: '忠誠', energy: 'エネルギー', experience: '経験', time: '時間', oil: '油', lore: '伝承', shield: '盾',
    stun: '麻痺', ki: '気', quest: '探索', level: 'レベル', page: 'ページ', fade: '消散', age: '年齢', storage: '貯蔵', finality: '終局', flood: '洪水', blood: '血' };
  const ZONES = [
    [/^(?:your |its owner's |their owner's |their |a |the )?graveyards?$/, '墓地'], [/^the battlefield$/, '戦場'],
    [/^(?:your |its owner's |their owner's |their |you )?hands?$/, '手札'], [/^(?:your )?library$/, 'ライブラリー'],
    [/^(?:the )?top of (?:your |its owner's |their owner's )?library$/, 'ライブラリーの一番上'], [/^the bottom of (?:your |its owner's )?library$/, 'ライブラリーの一番下'],
    [/^exile$/, '追放領域'], [/^the command zone$/, '統率領域'], [/^(?:an |each |target )?opponent's graveyard$/, '対戦相手の墓地'],
  ];
  const zone = s => { s = s.trim(); for (const [re, ja] of ZONES) if (re.test(s)) return ja; return null; };
  const CARD = /^«\d+»$/;
  const MANA = /^(\{[^{}]{1,6}\})+$/;

  // ---------------------------------------------------------------- nouns
  const SIMPLE = {
    'it': 'それ', 'itself': 'それ自身', 'them': 'それら', 'themselves': 'それら', 'you': 'あなた', 'each opponent': '各対戦相手',
    'target opponent': '対戦相手1人', 'an opponent': '対戦相手1人', 'each player': '各プレイヤー', 'any target': '1つを対象', 'any player': 'プレイヤー1人',
    'target player': 'プレイヤー1人', 'all opponents': 'すべての対戦相手', 'each other player': '他の各プレイヤー',
    'a creature': 'クリーチャー1体', 'another creature': '他のクリーチャー1体', 'a creature you control': 'あなたがコントロールするクリーチャー1体',
    'another creature you control': 'あなたがコントロールする他のクリーチャー1体', 'a nontoken creature': 'トークンでないクリーチャー1体',
    'a nontoken creature you control': 'あなたがコントロールするトークンでないクリーチャー1体', 'another nonland creature': '他の土地でないクリーチャー1体',
    'another nonland creature you control': 'あなたがコントロールする他の土地でないクリーチャー1体', 'a nonland creature': '土地でないクリーチャー1体',
    'any creature': '任意のクリーチャー1体', 'the creature': 'そのクリーチャー', 'that creature': 'そのクリーチャー', 'the creatures': 'それらのクリーチャー',
    'the creature token': 'そのクリーチャー・トークン', 'the creature tokens': 'それらのクリーチャー・トークン', 'a creature token': 'クリーチャー・トークン1体',
    'the token': 'そのトークン', 'that token': 'そのトークン', 'the tokens': 'それらのトークン', 'a token': 'トークン1つ', 'the land': 'その土地',
    'a land': '土地1つ', 'the lands': 'それらの土地', 'a land you control': 'あなたがコントロールする土地1つ', 'the card': 'そのカード', 'a card': 'カード1枚',
    'the spell': 'その呪文', 'the artifact': 'そのアーティファクト', 'an artifact': 'アーティファクト1つ', 'the artifact spell': 'そのアーティファクト呪文',
    'the persist creature': '頑強を持つそのクリーチャー', 'the undying creature': '不死を持つそのクリーチャー', 'the sacrificed creature': '生け贄に捧げたクリーチャー',
    'the creature it is attached to': 'それがつけられているクリーチャー', 'the copy': 'そのコピー', 'the ability': 'その能力', 'the trigger': 'その誘発型能力',
    'all creatures': 'すべてのクリーチャー', 'all creatures you control': 'あなたがコントロールするすべてのクリーチャー', 'each creature you control': 'あなたがコントロールする各クリーチャー',
    'each creature': '各クリーチャー', 'all other permanents you control': 'あなたがコントロールする他のすべてのパーマネント', 'the top card of your library': 'あなたのライブラリーの一番上のカード',
    'the earthbent land': '土変化した土地', 'the fetched land': 'サーチした土地', 'a nontoken creature card': 'トークンでないクリーチャー・カード1枚',
    'the mana-producing permanents': 'マナを生み出すパーマネント', 'a mana-producing permanent': 'マナを生み出すパーマネント1つ', 'the other token': 'もう1つのトークン',
    'a creature card': 'クリーチャー・カード1枚', 'another target creature': '他のクリーチャー1体を対象', 'target creature': 'クリーチャー1体を対象',
    'any number of creatures': '好きな数のクリーチャー', 'any number of lands': '好きな数の土地', 'any number of nonland permanents you control': 'あなたがコントロールする好きな数の土地でないパーマネント',
    'a Saproling': '苗木1体', 'the Saproling': 'その苗木', 'a Food': '食物1つ', 'the Food': 'その食物', 'a Clue': '手掛かり1つ', 'the Clue': 'その手掛かり',
    'the Servo': 'その霊気装置', 'the Soldier': 'その兵士', 'the Egg': 'その卵', 'the Eldrazi Spawn': 'そのエルドラージ・落とし子', 'the Treasure': 'その宝物',
    'the Treasures': 'それらの宝物', 'a Treasure': '宝物1つ', 'the Treasure token': 'その宝物・トークン', 'the Treasure tokens': 'それらの宝物・トークン',
    'the attacking creature': 'その攻撃クリーチャー', 'the blocking creature': 'そのブロック・クリーチャー', 'the equipped creature': '装備しているクリーチャー',
    'any other creature': '他の任意のクリーチャー1体', 'the basic land': 'その基本土地', 'any applicable target': '適正な対象', 'the animated Forest': 'クリーチャー化した森',
    'a creature an opponent controls': '対戦相手がコントロールするクリーチャー1体', 'the Forest tokens': 'それらの森・トークン', 'the enchanted creature': 'エンチャントされているクリーチャー', 'a permanent': 'パーマネント1つ', 'the permanent': 'そのパーマネント', 'the planeswalker': 'そのプレインズウォーカー',
    'any nontoken creature': 'トークンでない任意のクリーチャー1体', 'the creature castable for one mana': '1マナで唱えられるそのクリーチャー', 'the nontoken creature': 'そのトークンでないクリーチャー',
    'the artifact creature': 'そのアーティファクト・クリーチャー', 'any artifact creature': '任意のアーティファクト・クリーチャー1体', 'another nonland permanent': '他の土地でないパーマネント1つ',
    'a nonland permanent': '土地でないパーマネント1つ', 'any number of permanents': '好きな数のパーマネント', 'the mana-producing permanent': 'マナを生み出すそのパーマネント',
    'the spell': 'その呪文', 'the remaining trigger': '残っている誘発型能力', 'the first trigger': '1つ目の誘発型能力', 'the second trigger': '2つ目の誘発型能力',
    'a card in hand': '手札のカード1枚', 'the creature card': 'そのクリーチャー・カード', 'the land card': 'その土地カード', 'the artifact card': 'そのアーティファクト・カード',
    'the tapped creature': 'タップ状態のそのクリーチャー', 'the other creature': 'もう1体のクリーチャー', 'a nontoken artifact': 'トークンでないアーティファクト1つ',
    'all cards exiled with it': 'それによって追放されているすべてのカード', 'an equipment': '装備品1つ', 'an Equipment': '装備品1つ', 'the Equipment': 'その装備品',
    'your commander': 'あなたの統率者', 'the commander': 'その統率者', 'each creature an opponent controls': '対戦相手がコントロールする各クリーチャー',
    'all creatures your opponents control': '対戦相手がコントロールするすべてのクリーチャー', 'each opponent\'s library': '各対戦相手のライブラリー',
  };
  const BARE = { creature: 'クリーチャー', artifact: 'アーティファクト', land: '土地', enchantment: 'エンチャント', planeswalker: 'プレインズウォーカー', permanent: 'パーマネント',
    'nonland permanent': '土地でないパーマネント', 'artifact creature': 'アーティファクト・クリーチャー', 'nontoken creature': 'トークンでないクリーチャー', token: 'トークン', 'creature token': 'クリーチャー・トークン',
    Forest: '森', Island: '島', Mountain: '山', Plains: '平地', Swamp: '沼', 'basic land': '基本土地', 'Equipment': '装備品', Aura: 'オーラ', card: 'カード' };
  const unit = w => { const j = bare(w) || ''; const sg = String(w).replace(/ies$/, 'y').replace(/(?<=[^s])s$/, ''); return (/クリーチャー/.test(j) || TYPES[sg] || TYPES[w]) ? '体' : 'つ'; };
  const bare = w => { w = String(w || '').trim(); const sg = w.replace(/ies$/, 'y').replace(/(?<=[^s])s$/, ''); return BARE[w] || BARE[sg] || TYPES[sg] || TOKENS[sg] || TYPES[w] || TOKENS[w] || null; };
  function typeWords(s) {
    const words = s.split(' ');
    const out = [];
    let known = 0;
    for (const w of words) {
      const t = TYPES[w] || TOKENS[w] || ({ Forest: '森', Island: '島', Mountain: '山', Plains: '平地', Swamp: '沼' })[w];
      if (t) known++;
      out.push(t || w);
    }
    return known ? out.join('・') : out.join(' ');
  }
  const KIND = { creature: 'クリーチャー', artifact: 'アーティファクト', 'artifact creature': 'アーティファクト・クリーチャー', enchantment: 'エンチャント',
    land: '土地', 'enchantment creature': 'エンチャント・クリーチャー', 'legendary creature': '伝説のクリーチャー', 'artifact land': 'アーティファクト・土地' };
  function counter(kind, n) {
    const c = /^([+-]\d+\/[+-]\d+)$/.test(kind) ? kind : (COUNTERS[kind] ? COUNTERS[kind] : null);
    return c ? `${c}カウンター` : null;
  }
  // "two 1/1 green Saproling creature tokens with haste" and friends
  function tokenPhrase(s) {
    const m = s.match(/^(a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+|X)(?: (tapped|untapped))?(?: (\d+\/\d+))?(?: (?:white|blue|black|red|green|colorless|legendary))*(?: ([A-Z][\w'-]*(?: [A-Z][\w'-]*)*))?(?: (creature|artifact|artifact creature|enchantment|land|enchantment creature|legendary creature))? tokens?(?: with ([a-z ]+?))?(?: for each (.+))?$/);
    if (!m) return null;
    const [, count, state, pt, types, kind, kws, each] = m;
    const n = count === 'X' ? 'X' : num(count);
    if (n === null) return null;
    let name = '';
    if (types) { name = typeWords(types); if (!name) return null; }
    if (!name && !kind) name = '';
    const parts = [];
    if (kws) {
      const ks = kws.split(/, | and /).map(k => KW[k.trim()]);
      if (ks.some(k => !k)) return null;
      parts.push(ks.join('と') + 'を持つ');
    }
    if (state === 'tapped') parts.push('タップ状態の');
    if (state === 'untapped') parts.push('アンタップ状態の');
    if (pt) parts.push(pt + 'の');
    const noun = [name, kind ? KIND[kind] : ''].filter(Boolean).join('・');
    const isCreature = (kind || '').includes('creature');
    const unit = isCreature ? '体' : 'つ';
    let out = parts.join('') + (noun ? noun + '・' : '') + 'トークン' + n + unit;
    if (each) { const e = np(each); if (!e) return null; out = e + '1つにつき' + out; }
    return out;
  }
  function np(s) {
    s = String(s || '').trim().replace(/^the the /, 'the ').replace(/^(The|A|An|Another|Each|All|Target|Any|Both|One|Two|Three) /, w => w.toLowerCase());
    if (!s) return null;
    if (CARD.test(s) || /^«T\d+»$/.test(s)) return s;
    if (SIMPLE[s] !== undefined) return SIMPLE[s];
    let m;
    if ((m = s.match(/^(.+?)(?:, (.+?))*,? and (.+)$/)) && !/ (?:from|to|on|onto|into|with|of) /.test(s.replace(/«\d+»/g, 'X'))) {
      const items = s.split(/, and |, | and /).map(np);
      if (items.every(Boolean)) return items.join('と');
    }
    if ((m = s.match(/^the («\d+») (token|tokens|ability|abilities|trigger|triggers|copy|spell|emblem)$/))) return `${m[1]}の${{ token: 'トークン', tokens: 'トークン', ability: '能力', abilities: '能力', trigger: '誘発型能力', triggers: '誘発型能力', copy: 'コピー', spell: '呪文', emblem: '紋章' }[m[2]]}`;
    if ((m = s.match(/^(?:a|one) token copy of (.+)$/))) { const x = np(m[1]); return x && `${x}のトークン・コピー1つ`; }
    if ((m = s.match(/^(two|three|four|five|\d+) token copies of (.+)$/))) { const x = np(m[2]); return x && `${x}のトークン・コピー${num(m[1])}つ`; }
    if ((m = s.match(/^a copy of (.+)$/))) { const x = np(m[1]); return x && `${x}のコピー1つ`; }
    if ((m = s.match(/^the copy of (.+)$/))) { const x = np(m[1]); return x && `${x}のコピー`; }
    if ((m = s.match(/^(?:the )?(top|bottom) (two|three|four|five|six|seven|\d+) cards of your library$/))) return `あなたのライブラリーの${m[1] === 'top' ? '一番上' : '一番下'}から${num(m[2])}枚のカード`;
    if ((m = s.match(/^(a|one|two|three|four|five|six|seven|eight|\d+) (?:of the )?(Treasures?|Clues?|Foods?|Blood tokens?|Treasure tokens?|Clue tokens?|Food tokens?|Squirrels?|tokens?|creature tokens?|artifact tokens?|lands?|creatures?|Servos?|Saprolings?|Eldrazi Spawn|Soldiers?|Rats?)$/))) {
      const word = m[2].replace(/ tokens?$/, '').replace(/s$/, '');
      const base = { Treasure: '宝物', Clue: '手掛かり', Food: '食物', Blood: '血', token: 'トークン', 'creature token': 'クリーチャー・トークン', 'artifact token': 'アーティファクト・トークン',
        land: '土地', creature: 'クリーチャー', Servo: '霊気装置', Saproling: '苗木', 'Eldrazi Spawn': 'エルドラージ・落とし子', Soldier: '兵士', Rat: 'ネズミ', Squirrel: 'リス' }[word];
      if (base) return `${base}${num(m[1])}${/creature|Soldier|Rat|Squirrel|Saproling|Spawn|Servo/.test(word) ? '体' : 'つ'}`;
    }
    if ((m = s.match(/^(?:both|all|the) (Treasures|tokens|creature tokens|lands|Clues|Foods)$/))) return `すべての${{ Treasures: '宝物', tokens: 'トークン', 'creature tokens': 'クリーチャー・トークン', lands: '土地', Clues: '手掛かり', Foods: '食物' }[m[1]]}`;
    if ((m = s.match(/^(?:a|an|one|two|three|four|five|six|seven|eight|\d+|X)(?: (?:tapped|untapped))?(?: \d+\/\d+)?.* tokens?(?: with [a-z ,]+?)?(?: for each .+)?$/))) { const t = tokenPhrase(s); if (t) return t; }
    if ((m = s.match(/^(?:a|an|the) ([A-Z][\w'-]*(?: [A-Z][\w'-]*)*) token$/))) { const t = typeWords(m[1]); if (t) return `${s.startsWith('the') ? 'その' : ''}${t}・トークン${s.startsWith('the') ? '' : '1つ'}`; }
    if ((m = s.match(/^(a|an|one|two|three|\d+) ([+-]\d+\/[+-]\d+|charge|loyalty|energy|oil|time|lore|shield|stun) counters?$/))) { const c = counter(m[2]); return c && `${c}${num(m[1])}個`; }
    if ((m = s.match(/^(.+?) you control$/)) && SIMPLE[m[1]] === undefined) { const x = np(m[1]); if (x && !x.includes('あなた')) return `あなたがコントロールする${x.replace(/1(体|つ)$/, '')}`; }
    if ((m = s.match(/^another (.+)$/))) { const x = np('a ' + m[1]); return x && `他の${x}`; }
    if ((m = s.match(/^(?:a|an) (artifact|creature|enchantment|land|planeswalker|permanent|instant|sorcery) card$/))) return `${{ artifact: 'アーティファクト', creature: 'クリーチャー', enchantment: 'エンチャント', land: '土地', planeswalker: 'プレインズウォーカー', permanent: 'パーマネント', instant: 'インスタント', sorcery: 'ソーサリー' }[m[1]]}・カード1枚`;
    if ((m = s.match(/^(?:a|an) (artifact|enchantment|planeswalker|permanent)$/))) return `${{ artifact: 'アーティファクト', enchantment: 'エンチャント', planeswalker: 'プレインズウォーカー', permanent: 'パーマネント' }[m[1]]}1つ`;
    if ((m = s.match(/^(?:a|an|one) ([A-Z][\w'-]*)$/)) && (TYPES[m[1]] || TOKENS[m[1]])) return `${TYPES[m[1]] || TOKENS[m[1]]}1${TYPES[m[1]] ? '体' : 'つ'}`;
    if ((m = s.match(/^the ([A-Z][\w'-]*)s?$/)) && (TYPES[m[1]] || TOKENS[m[1]])) return `その${TYPES[m[1]] || TOKENS[m[1]]}`;
    if ((m = s.match(/^«T(\d+)»$/))) return s;
    if ((m = s.match(/^the creature (?:with|that has) (.+?) attached$/))) { const x = np(m[1]); return x && `${x}がつけられたクリーチャー`; }
    if ((m = s.match(/^(?:one|a single) of the («\d+») tokens$/))) return `${m[1]}のトークン1つ`;
    if ((m = s.match(/^the other («\d+») token$/))) return `もう1つの${m[1]}のトークン`;
    if ((m = s.match(/^up to (two|three|four|five|six|seven|eight|nine|ten|\d+) (.+?)s?$/)) && bare(m[2])) return `最大${num(m[1])}${bare(m[2]) === '土地' ? 'つの' : 'つの'}${bare(m[2])}`;
    if ((m = s.match(/^any number of (.+?)s?(?: you control)?$/)) && bare(m[1])) return `${/you control$/.test(s) ? 'あなたがコントロールする' : ''}好きな数の${bare(m[1])}`;
    if ((m = s.match(/^(two|three|four|five|six|seven|eight|\d+) ([A-Z][\w'-]*?)s?$/)) && (TYPES[m[2]] || TOKENS[m[2]])) return `${TYPES[m[2]] || TOKENS[m[2]]}${num(m[1])}${TYPES[m[2]] ? '体' : 'つ'}`;
    if ((m = s.match(/^the ([A-Z][\w'-]*?)s$/)) && (TYPES[m[1]] || TOKENS[m[1]])) return `それらの${TYPES[m[1]] || TOKENS[m[1]]}`;
    if ((m = s.match(/^(?:a|an) ([A-Z][\w'-]*)$/)) && bare(m[1])) return `${bare(m[1])}1つ`;
    if ((m = s.match(/^([A-Z][\w'-]*) you control$/)) && bare(m[1])) return `あなたがコントロールする${bare(m[1])}`;
    if ((m = s.match(/^(five|four|three|two|six|seven|\d+) of the (artifact tokens|creature tokens|tokens|Treasures|lands)$/))) return `${{ 'artifact tokens': 'アーティファクト・トークン', 'creature tokens': 'クリーチャー・トークン', tokens: 'トークン', Treasures: '宝物', lands: '土地' }[m[2]]}${num(m[1])}つ`;
    if ((m = s.match(/^(.+?)'s? trigger$/))) { const x = np(m[1]); return x && `${x}の誘発型能力`; }
    if ((m = s.match(/^the (first|second|third) («\d+») trigger$/))) return `${ORD[m[1]]}${m[2]}の誘発型能力`;
    if ((m = s.match(/^a (.+) named («\d+»)$/))) return `${m[2]}という名前の${m[1] === 'card' ? 'カード' : m[1]}`;
    return null;
  }

  // ---------------------------------------------------------------- verbs
  function mana(s) {
    s = s.trim();
    let m;
    if (MANA.test(s)) return s;
    if ((m = s.match(/^at least (\{.+\})$/)) && MANA.test(m[1])) return `少なくとも${m[1]}`;
    if (/^one mana of any color$/.test(s)) return '好きな色のマナ1点';
    if (/^(?:one|a) mana$/.test(s)) return 'マナ1点';
    if ((m = s.match(/^(two|three|four|five|six|seven|\d+) mana of any (?:one )?colou?r$/))) return `好きな色のマナ${num(m[1])}点`;
    if ((m = s.match(/^(two|three|four|five|six|seven|\d+) mana$/))) return `マナ${num(m[1])}点`;
    if ((m = s.match(/^an amount of (\{.+\})$/)) && MANA.test(m[1])) return `一定量の${m[1]}`;
    if ((m = s.match(/^at least enough mana to cast («\d+»)$/))) return `${m[1]}を唱えるのに十分なマナ`;
    if ((m = s.match(/^(.+?) that cannot be spent to pay generic mana costs$/))) { const x = mana(m[1]); return x && `${x}（不特定マナ・コストには使えない）`; }
    if ((m = s.match(/^(\{.+\}) for each (.+)$/)) && MANA.test(m[1])) { const x = np(m[2]); return x && `${x}1つにつき${m[1]}`; }
    return null;
  }
  function life(s) {
    const m = s.match(/^(\d+|one|two|three|four|five|X) life$/);
    return m ? `${num(m[1]) ?? m[1]}点のライフ` : null;
  }
  // a payment: "{2}", "its mana cost", "2 life", "{1} and 2 life"
  function payment(s) {
    s = s.trim();
    if (/^its (?:mana )?cost$/.test(s)) return 'マナ・コスト';
    if (/^its (?:mana cost|cost) plus commander tax(?:, if applicable)?$/.test(s)) return 'マナ・コストと統率者税';
    if (/^(\{.+\}) plus commander tax(?:, if applicable)?$/.test(s) && MANA.test(s.split(' ')[0])) return `${s.split(' ')[0]}と統率者税`;
    let mm;
    if ((mm = s.match(/^at most (\{.+\})$/)) && MANA.test(mm[1])) return `最大${mm[1]}`;
    if ((mm = s.match(/^one mana$/))) return 'マナ1点';
    const parts = s.split(/ and |, /).map(p => mana(p) || life(p) || (p === 'its mana cost' ? 'マナ・コスト' : null));
    if (parts.length && parts.every(Boolean)) return parts.join('と');
    return null;
  }
  // "X from Z1 to Z2", with the extras that follow a move
  function moveTail(s) {
    let extra = '', m;
    if ((m = s.match(/^(.*) tapped$/))) { s = m[1]; extra += 'タップ状態で'; }
    if ((m = s.match(/^(.*) with (a|an|one|two) ([+-]\d+\/[+-]\d+) counters? on it$/))) { s = m[1]; extra = `${m[3]}カウンターが${num(m[2])}個置かれた状態で` + extra; }
    if ((m = s.match(/^(.*) without (?:a|an) ([+-]\d+\/[+-]\d+) counter on it(?: due to (.+))?$/))) { s = m[1]; extra = `${m[2]}カウンターが置かれずに` + extra; }
    if ((m = s.match(/^(.*) attached to (.+)$/))) { const t = np(m[2]); if (!t) return null; s = m[1]; extra = `${t}につけられた状態で` + extra; }
    if ((m = s.match(/^(.*) under your control$/))) { s = m[1]; extra = 'あなたのコントロール下で' + extra; }
    return { rest: s, extra };
  }
  // dictionary-form Japanese for a verb phrase ("create a Treasure token", "creating …")
  function vp(s, subj = '') {
    s = String(s || '').trim().replace(/\.$/, '');
    if (!s) return null;
    let m;
    const due = s.match(/^(.*) (?:due to|thanks to) (.+)$/);
    if (due) { const why = np(due[2]) || reasonNp(due[2]); const r = vp(due[1], subj); return why && r ? `${r}（${why}により）` : null; }
    const chain = splitChain(s);
    if (chain.length > 1) { const parts = chain.map(p => vp(p, subj)); return parts.every(Boolean) ? joinClauses(parts) : null; }
    const w = s.replace(/^(?:then |and )/, '');
    if (w !== s) return vp(w, subj);
    // mana
    if ((m = w.match(/^add(?:ing)? (.+)$/))) { const x = mana(m[1]); return x && `${x}を加える`; }
    if ((m = w.match(/^(?:creat(?:e|ing)) (.+)$/))) { const x = np(m[1]); return x && `${x}を生成する`; }
    if ((m = w.match(/^(?:return(?:ing)?) (.+?) from (.+?) (?:to|onto) (.+)$/))) {
      const t = moveTail(m[3]); if (!t) return null;
      const x = np(m[1]), a = zone(m[2]), b = zone(t.rest);
      return x && a && b && `${x}を${a}から${t.extra}${b}に戻す`;
    }
    if ((m = w.match(/^(?:return(?:ing)?) (.+?) to (.+)$/))) { const t = moveTail(m[2]); const x = np(m[1]), b = t && zone(t.rest); return x && b && `${x}を${t.extra}${b}に戻す`; }
    if ((m = w.match(/^(?:put(?:ting)?) (a|an|one|two|three|four|five|X|\d+) ([+-]\d+\/[+-]\d+|charge|loyalty|energy|oil|time|lore|shield|stun) counters? on (.+)$/))) {
      const c = counter(m[2]), x = np(m[3]); return c && x && `${x}に${c}を${m[1] === 'X' ? 'X' : num(m[1])}個置く`;
    }
    if ((m = w.match(/^(?:put(?:ting)?) (.+?)'s ([+-]\d+\/[+-]\d+) counters on (.+)$/))) { const x = np(m[1]), y = np(m[3]); return x && y && `${x}の${m[2]}カウンターを${y}に置く`; }
    if ((m = w.match(/^(?:put(?:ting)?) (.+?) on top of (?:your|its owner's) library$/))) { const x = np(m[1]); return x && `${x}をライブラリーの一番上に置く`; }
    if ((m = w.match(/^(?:put(?:ting)?) (.+?) from (.+?) (?:onto|into|on) (.+)$/))) {
      const t = moveTail(m[3]); const x = np(m[1]), a = zone(m[2]), b = t && zone(t.rest);
      return x && a && b && `${x}を${a}から${t.extra}${b}に置く`;
    }
    if ((m = w.match(/^(?:put(?:ting)?) (.+?) (?:onto|into) (.+)$/))) { const t = moveTail(m[2]); const x = np(m[1]), b = t && zone(t.rest); return x && b && `${x}を${t.extra}${b}に置く`; }
    if ((m = w.match(/^(?:untap(?:ping)?) (.+)$/))) { const x = np(m[1]); return x && `${x}をアンタップする`; }
    if ((m = w.match(/^(?:tap(?:ping)?) (.+)$/))) { const x = np(m[1]); return x && `${x}をタップする`; }
    if ((m = w.match(/^(?:blink(?:ing)?) (.+)$/))) { const x = np(m[1]); return x && `${x}を明滅させる`; }
    if ((m = w.match(/^(?:target(?:ing)?) (.+)$/))) { const x = np(m[1]); return x && `${x}を対象とする`; }
    if ((m = w.match(/^(?:copy|copying) (.+?)(?:, with the copy targeting (.+))?$/))) { const x = np(m[1]); if (!x) return null; if (m[2]) { const y = np(m[2]); return y && `${x}をコピーし、そのコピーは${y}を対象とする`; } return `${x}をコピーする`; }
    if ((m = w.match(/^(?:exil(?:e|ing)) (.+?)(?: until (.+?) leaves the battlefield)?(?: with the ability to (?:play|cast) (?:them|it) (?:until (?:your next end step|end of turn)|later from exile))?$/))) {
      const x = np(m[1]); if (!x) return null; if (m[2]) { const y = np(m[2]); return y && `${y}が戦場を離れるまで${x}を追放する`; } return `${x}を追放する`;
    }
    if ((m = w.match(/^(?:destroy(?:ing)?) (.+)$/))) { const x = np(m[1]); return x && `${x}を破壊する`; }
    if ((m = w.match(/^(?:sacrific(?:e|ing)) (.+)$/))) { const x = np(m[1]); return x && `${x}を生け贄に捧げる`; }
    if ((m = w.match(/^(?:discard(?:ing)?) (.+)$/))) { const x = np(m[1]); return x && `${x}を捨てる`; }
    if ((m = w.match(/^(?:deal(?:ing)?) (\d+|X|one|two|three) damage to (.+)$/))) { const x = np(m[2]); return x && `${x}に${num(m[1]) ?? m[1]}点のダメージを与える`; }
    if ((m = w.match(/^(?:draw(?:ing)?) (a|one|two|three|four|five|\d+) cards?$/))) return `カードを${num(m[1])}枚引く`;
    if ((m = w.match(/^(?:gain(?:ing)?) (\d+|one|two|three|X) life$/))) return `${num(m[1]) ?? 'X'}点のライフを得る`;
    if (/^(?:gain(?:ing)?) life$/.test(w)) return 'ライフを得る';
    if ((m = w.match(/^(?:los(?:e|ing)) (\d+|one|two|three|X) life$/))) return `${num(m[1]) ?? 'X'}点のライフを失う`;
    if ((m = w.match(/^(?:mill(?:ing)?) (a|one|two|three|four|five|six|seven|\d+|at least \w+) cards?$/))) return `カードを${m[1].startsWith('at least') ? '少なくとも' + num(m[1].slice(9)) : num(m[1])}枚切削する`;
    if ((m = w.match(/^(?:scry(?:ing)?) (\d+)$/))) return `占術${m[1]}を行う`;
    if ((m = w.match(/^(?:surveil(?:ing|ling)?) (\d+)$/))) return `諜報${m[1]}を行う`;
    if ((m = w.match(/^(?:proliferat(?:e|ing))$/))) return '増殖を行う';
    if ((m = w.match(/^(?:get(?:ting)?) (.+)$/)) && mana(m[1])) return `${mana(m[1])}を得る`;
    if (/^win the game$/.test(w)) return 'ゲームに勝利する';
    if ((m = w.match(/^choosing not to put anything from your hand onto the battlefield$/)) || /^choosing to put nothing onto the battlefield$/.test(w)) return '何も戦場に出さないことを選ぶ';
    if ((m = w.match(/^choosing not to pay$/))) return '支払わないことを選ぶ';
    if ((m = w.match(/^(?:pay(?:ing)?) (.+?) to copy (.+?)'s ability$/))) { const p = payment(m[1]), x = np(m[2]); return p && x && `${p}を支払って${x}の能力をコピーする`; }
    if ((m = w.match(/^(?:pay(?:ing)?) (.+?) to return (.+?) to the battlefield from (.+)$/))) { const p = payment(m[1]), x = np(m[2]), z = zone(m[3]); return p && x && z && `${p}を支払って${x}を${z}から戦場に戻す`; }
    if ((m = w.match(/^(?:pay(?:ing)?) (.+?) to create (.+)$/))) { const p = payment(m[1]), x = np(m[2]); return p && x && `${p}を支払って${x}を生成する`; }
    if ((m = w.match(/^(?:pay(?:ing)?) (.+)$/))) { const p = payment(m[1]); return p && `${p}を支払う`; }
    if (/^take an extra turn after this one$/.test(w)) return 'このターンの後に追加のターンを1回行う';
    if (/^get an additional combat phase after this one$/.test(w)) return 'このフェイズの後に追加の戦闘フェイズを得る';
    if ((m = w.match(/^untap all (.+)$/))) { const x = np('all ' + m[1]); return x && `${x}をアンタップする`; }
    if ((m = w.match(/^(?:cast(?:ing)?) (.+?) from (.+?) without paying its mana cost$/))) { const x = np(m[1]), z = zone(m[2]); return x && z && `${z}から${x}をマナ・コストを支払うことなく唱える`; }
    if ((m = w.match(/^(?:cast(?:ing)?) (.+?) without paying its mana cost$/))) { const x = np(m[1]); return x && `${x}をマナ・コストを支払うことなく唱える`; }
    if ((m = w.match(/^allowing you to cast (.+?) from (.+?)(?: this turn)?$/))) { const x = np(m[1]), z = zone(m[2]); return x && z && `${z}から${x}を唱えられるようにする`; }
    if ((m = w.match(/^allowing you to use its ability again this turn$/))) return 'このターン、その能力をもう一度使えるようにする';
    if ((m = w.match(/^(?:giv(?:e|ing)) (.+?) ([+-]\d+\/[+-]\d+) until end of turn$/))) { const x = np(m[1]); return x && `ターン終了時まで${x}に${m[2]}の修整を与える`; }
    if ((m = w.match(/^(?:putting) nothing onto the battlefield$/))) return '何も戦場に出さない';
    if ((m = w.match(/^(?:triggering) each of their (first|second|third) abilities$/))) return `それぞれの${ORD[m[1]]}能力を誘発させる`;
    if ((m = w.match(/^(?:triggering) (.+)$/))) { const x = np(m[1]); return x && `${x}を誘発させる`; }
    if ((m = w.match(/^(?:attach(?:ing)?) (.+?) to (.+)$/))) { const x = np(m[1]), y = np(m[2]); return x && y && `${x}を${y}につける`; }
    if ((m = w.match(/^(?:reveal(?:ing)?) (.+)$/))) { const x = np(m[1]); return x && `${x}を公開する`; }
    if ((m = w.match(/^(?:shuffl(?:e|ing)) (?:your library|it into your library)$/))) return 'ライブラリーを切り直す';
    if ((m = w.match(/^(?:search(?:ing)?) your library for (.+)$/))) { const x = np(m[1]); return x && `ライブラリーから${x}を探す`; }
    if ((m = w.match(/^(?:double|doubling) any tokens you create this turn$/))) return 'このターンに生成するトークンを倍にする';
    if ((m = w.match(/^(?:causing|making|allowing) (you|it|each opponent|each player|target opponent|an opponent|«\d+») to (.+)$/))) {
      // "causing each opponent to lose 2 life and you to gain 2 life"
      const bits = (m[1] + ' to ' + m[2]).split(/ and (?=(?:you|it|each opponent|each player|target opponent|an opponent|«\d+») to )/);
      const out = [];
      for (const b of bits) {
        const k = b.match(/^(you|it|each opponent|each player|target opponent|an opponent|«\d+») to (.+)$/);
        if (!k) return null;
        const who = k[1] === 'you' ? (bits.length > 1 ? 'あなたは' : '') : (np(k[1]) + 'は');
        // "draw a card and put X on top", "untap … and to get …"
        const verbs = k[2].split(/ and (?:to )?(?=(?:put|return|draw|lose|gain|create|sacrifice|discard|mill|exile|untap|tap|search|shuffle|get|reveal|attach|cast|deal|scry|surveil)\b)|, then (?:to )?/);
        const vs = verbs.map(x => vp(x));
        if (!vs.every(Boolean)) return null;
        out.push(who + joinClauses(vs));
      }
      return joinClauses(out);
    }
    return null;
  }
  const ABIL = { persist: '頑強', undying: '不死', modular: '接合', fabricate: '製造', soulbond: '結魂', evolve: '進化', exploit: '濫用', landfall: '上陸', cycling: 'サイクリング',
    first: '1つ目の', second: '2つ目の', third: '3つ目の', ninjutsu: '忍術', unearth: '蘇生', flashback: 'フラッシュバック', escape: '脱出', buyback: 'バイバック' };
  function reasonNp(s) {
    s = s.trim();
    if (/^its replacement effect$/.test(s)) return 'その置換効果';
    if (/^the legend rule$/.test(s)) return 'レジェンド・ルール';
    if (/^(?:its|their) (\w+) ability$/.test(s)) { const k = s.match(/^(?:its|their) (\w+) ability$/)[1]; return ABIL[k] ? `${ABIL[k]}能力` : null; }
    if ((s.match(/^the (two|three|four) token doublers(?: and (.+))?$/))) return 'トークンを倍にする効果';
    return null;
  }
  // "adding {C}{C}, creating …, then …" → separate clauses
  const PARTICIPLE = /^(?:adding|creating|returning|untapping|tapping|blinking|putting|causing|targeting|copying|exiling|destroying|sacrificing|discarding|dealing|drawing|gaining|losing|milling|scrying|surveiling|paying|allowing|triggering|attaching|revealing|searching|making|then|and then|doubling|proliferating|casting)\b/;
  function splitChain(s) {
    const parts = s.split(/, (?=(?:and |then |and then )?(?:adding|creating|returning|untapping|blinking|putting|causing|targeting|copying|exiling|destroying|dealing|drawing|gaining|losing|milling|allowing|triggering|attaching|then|making|doubling|casting)\b)| and (?=(?:adding|creating|returning|untapping|blinking|putting|causing|exiling|destroying|dealing|drawing|gaining|losing|milling|creating|attaching|doubling)\b)/);
    return parts.map(p => p.trim()).filter(Boolean);
  }
  // join dictionary-form clauses into one sentence: "Aし、Bし、C"
  function renyou(v) {
    // dictionary form → continuative form for the common endings used here
    const pairs = [['する', 'し'], ['加える', '加え'], ['戻す', '戻し'], ['置く', '置き'], ['引く', '引き'], ['得る', '得'], ['失う', '失い'], ['与える', '与え'],
      ['捧げる', '捧げ'], ['捨てる', '捨て'], ['唱える', '唱え'], ['つける', 'つけ'], ['させる', 'させ'], ['探す', '探し'], ['行う', '行い'], ['支払う', '支払い'], ['移る', '移り']];
    for (const [a, b] of pairs) if (v.endsWith(a)) return v.slice(0, -a.length) + b;
    return null;
  }
  function joinClauses(parts) {
    const out = [];
    for (let i = 0; i < parts.length; i++) {
      if (i < parts.length - 1) {
        const r = renyou(parts[i].replace(/（[^）]*）$/, ''));
        if (!r) return parts.join('。');
        out.push(r + (parts[i].match(/（[^）]*）$/) || [''])[0] + '、');
      } else out.push(parts[i]);
    }
    return out.join('');
  }
  // te-form for "by tapping it and sacrificing X": "それをタップして、Xを生け贄に捧げて"
  function teForm(v) {
    const pairs = [['する', 'して'], ['加える', '加えて'], ['戻す', '戻して'], ['置く', '置いて'], ['引く', '引いて'], ['得る', '得て'], ['失う', '失って'], ['与える', '与えて'],
      ['捧げる', '捧げて'], ['捨てる', '捨てて'], ['唱える', '唱えて'], ['つける', 'つけて'], ['させる', 'させて'], ['支払う', '支払って'], ['取り除く', '取り除いて'], ['行う', '行って'], ['移る', '移って']];
    for (const [a, b] of pairs) if (v.endsWith(a)) return v.slice(0, -a.length) + b;
    return null;
  }
  // the "by …" part of "Activate X by …" / "Cast X by …"
  function byPart(s) {
    s = s.trim();
    let m;
    if ((m = s.match(/^tapping and sacrificing (.+)$/))) { const x = np(m[1]); return x && `${x}をタップして生け贄に捧げて`; }
    if ((m = s.match(/^removing (a|an|one|two|three|four|five|X|\d+) ([+-]\d+\/[+-]\d+|charge|loyalty|energy|oil|time|lore) counters? from (.+)$/))) {
      const c = counter(m[2]), x = np(m[3]); return c && x && `${x}から${c}を${m[1] === 'X' ? 'X' : num(m[1])}個取り除いて`;
    }
    if ((m = s.match(/^removing a counter from (.+)$/))) { const x = np(m[1]); return x && `${x}からカウンターを1個取り除いて`; }
    if ((m = s.match(/^putting (a|an|one|two) ([+-]\d+\/[+-]\d+) counters? on (.+)$/))) { const x = np(m[3]); return x && `${x}に${m[2]}カウンターを${num(m[1])}個置いて`; }
    if ((m = s.match(/^returning (.+?) from (.+?) to (.+)$/))) { const x = np(m[1]), a = zone(m[2]), b = zone(m[3]); return x && a && b && `${x}を${a}から${b}に戻して`; }
    if ((m = s.match(/^paying (.+?) and (tapping|sacrificing|exiling|discarding|untapping|removing|putting|returning) (.+)$/)) && payment(m[1])) {
      const rest = byPart(m[2] + ' ' + m[3]); return rest && `${payment(m[1])}を支払い、${rest}`;
    }
    const pieces = s.split(/,? and (?=tapping|sacrificing|paying|exiling|discarding|removing|untapping)|, (?=tapping|sacrificing|paying|exiling|discarding|removing|untapping)/);
    if (pieces.length > 1) { const p = pieces.map(byPart); return p.every(Boolean) ? p.join('、') : null; }
    if ((m = s.match(/^paying (.+)$/))) { const p = payment(m[1]); return p && `${p}を支払って`; }
    if ((m = s.match(/^tapping (.+)$/))) { const x = np(m[1]); return x && `${x}をタップして`; }
    if ((m = s.match(/^untapping (.+)$/))) { const x = np(m[1]); return x && `${x}をアンタップして`; }
    if ((m = s.match(/^sacrificing (.+)$/))) { const x = np(m[1]); return x && `${x}を生け贄に捧げて`; }
    if ((m = s.match(/^exiling (.+?)(?: from (.+))?$/))) { const x = np(m[1]); const z = m[2] ? zone(m[2]) : ''; return x && z !== null && `${z ? z + 'から' : ''}${x}を追放して`; }
    if ((m = s.match(/^discarding (.+)$/))) { const x = np(m[1]); return x && `${x}を捨てて`; }
    return null;
  }
  // "«0»'s second ability" → owner «0», label "2つ目の能力"; "«0»" → owner «0», no label
  function abilityOf(s) {
    let m;
    if ((m = s.match(/^(.+?)'s? (first|second|third|fourth|fifth|last) (?:loyalty )?(?:ability|abiltiy)$/))) { const x = np(m[1]); return x && { owner: x, label: `${ORD[m[2]]}${/loyalty/.test(s) ? '忠誠度' : ''}能力` }; }
    if ((m = s.match(/^(.+?)'s (cycling|ninjutsu|unearth|channel|equip|crew|boast|exhaust) ability$/))) { const x = np(m[1]); return x && { owner: x, label: `${{ cycling: 'サイクリング', ninjutsu: '忍術', unearth: '蘇生', channel: '魂力', equip: '装備', crew: '搭乗', boast: '誇示', exhaust: '消尽' }[m[2]]}能力` }; }
    if ((m = s.match(/^(.+?)'s ability$/))) { const x = np(m[1]); return x && { owner: x, label: '能力' }; }
    const x = np(s); return x && { owner: x, label: '' };
  }
  // ---------------------------------------------------------------- sentences
  function sentence(s) {
    s = s.trim().replace(/\.$/, '').trim();
    if (!s) return null;
    let m, pre = '';
    if ((m = s.match(/^Holding priority, (.+)$/i))) { pre = '優先権を保持したまま、'; s = m[1].charAt(0).toUpperCase() + m[1].slice(1); }
    if ((m = s.match(/^During an opponent's turn, (.+)$/i))) { pre += '対戦相手のターンに、'; s = m[1].charAt(0).toUpperCase() + m[1].slice(1); }
    const r = main(s);
    return r ? pre + r : null;
  }
  function withTail(head, tail) {
    if (!tail) return head;
    const t = vp(tail);
    if (!t) return null;
    const h = renyou(head.replace(/（[^）]*）$/, ''));
    return h ? h + (head.match(/（[^）]*）$/) || [''])[0] + '、' + t : null;
  }
  const STATES = [
    [/^(.+?) (?:does not|doesn't|do not|don't) have summoning sickness$/, x => np(x) && `${np(x)}は召喚酔いしていない`],
    [/^(.+?) (?:has|have) haste$/, x => np(x) && `${np(x)}は速攻を持っている`],
    [/^(.+?) (?:is )?attached to (.+)$/, (x, y) => np(x) && np(y) && `${np(x)}が${np(y)}につけられている`],
    [/^You have a way to gain life$/, () => 'ライフを得る手段がある'],
    [/^You have a way to draw a card$/, () => 'カードを引く手段がある'],
    [/^You have a way to cause a creature to enter the battlefield under your control$/, () => 'クリーチャーをあなたのコントロール下で戦場に出す手段がある'],
    [/^You have a way to (.+)$/, x => vp(x) && `${vp(x)}手段がある`],
    [/^Your life total is (?:at least )?(\d+)(?: or (?:higher|greater|more))?$/, x => `あなたのライフ総量が${x}点以上である`],
    [/^You have (\d+) or more life$/, x => `あなたのライフが${x}点以上ある`],
    [/^You are able to play a land this turn$/, () => 'このターン、土地をプレイできる'],
    [/^(?:An|At least one) opponent cannot block creatures you control$/, () => '対戦相手はあなたのクリーチャーをブロックできない'],
    [/^An opponent cannot block and kill (.+)$/, x => np(x) && `対戦相手は${np(x)}をブロックして倒せない`],
    [/^You control (?:at least )?(one|two|three|four|five|\d+) (?:additional|other) creatures?$/, n => `あなたは他のクリーチャーを${num(n)}体以上コントロールしている`],
    [/^You control (?:an|another) (?:additional )?(creature|nonland creature)$/, k => `あなたは他の${k === 'creature' ? '' : '土地でない'}クリーチャーをコントロールしている`],
    [/^You control at least (one|two|three|four|five|\d+) (.+)$/, (n, x) => { const y = np(x.replace(/s$/, '')) || TYPES[x.replace(/s$/, '')] || TOKENS[x.replace(/s$/, '')]; return y && `あなたは${y.replace(/1(体|つ)$/, '')}を${num(n)}つ以上コントロールしている`; }],
    [/^You control (.+)$/, x => np(x) && `あなたは${/^(?:a|an) /.test(x) ? np(x).replace(/1(体|つ)$/, '') : np(x)}をコントロールしている`],
    [/^(.+?) has attacked this turn$/, x => np(x) && `${np(x)}はこのターンに攻撃している`],
    [/^You have attacked this turn$/, () => 'このターン、あなたは攻撃している'],
    [/^It is not your turn$/, () => 'あなたのターンではない'],
    [/^It is an opponent's turn$/, () => '対戦相手のターンである'],
    [/^It is your turn$/, () => 'あなたのターンである'],
    [/^You have a land card in hand$/, () => '手札に土地カードがある'],
    [/^You have a card in hand$/, () => '手札にカードがある'],
    [/^You have (?:a|an) (.+?) card in your graveyard$/, x => `あなたの墓地に${{ creature: 'クリーチャー', artifact: 'アーティファクト', land: '土地', instant: 'インスタント', sorcery: 'ソーサリー' }[x] || x}・カードがある`],
    [/^There(?: is|'s) (?:a|an) (.+?) card in your graveyard$/, x => `あなたの墓地に${{ creature: 'クリーチャー', artifact: 'アーティファクト', land: '土地' }[x] || x}・カードがある`],
    [/^You have at least (one|two|three|four|five|\d+) other cards in your graveyard$/, n => `あなたの墓地に他のカードが${num(n)}枚以上ある`],
    [/^You have enough mana to cast (.+)$/, x => np(x) && `${np(x)}を唱えるのに十分なマナがある`],
    [/^You have at least (\{.+\})$/, x => `少なくとも${x}を出せる`],
    [/^(.+?) can tap to produce at least (\{.+\})$/, (x, y) => { const z = x === 'Lands you control' ? 'あなたの土地' : x === 'Creatures you control' ? 'あなたのクリーチャー' : np(x); return z && `${z}をタップして少なくとも${y}を出せる`; }],
    [/^(.+?) has at least one ([+-]\d+\/[+-]\d+) counter on it$/, (x, c) => np(x) && `${np(x)}に${c}カウンターが1個以上置かれている`],
    [/^(.+?) (?:does not|doesn't) have (?:a|any) ([+-]\d+\/[+-]\d+) counters? on it$/, (x, c) => np(x) && `${np(x)}に${c}カウンターが置かれていない`],
    [/^You are not currently venturing in a dungeon$/, () => 'ダンジョンを探索中ではない'],
    [/^(.+?) is a copy of (.+)$/, (x, y) => np(x) && np(y) && `${np(x)}は${np(y)}のコピーである`],
    [/^An opponent controls a creature$/, () => '対戦相手がクリーチャーをコントロールしている'],
    [/^There is a removable counter on a creature you control$/, () => 'あなたのクリーチャーに取り除けるカウンターが置かれている'],
    [/^All permanents are on the battlefield$/, () => 'すべてのパーマネントが戦場にある'],
    [/^(.+?) (?:is|are) on the battlefield$/, x => np(x) && `${np(x)}が戦場にある`],
    [/^(.+?) (?:is|are) in your graveyard$/, x => np(x) && `${np(x)}があなたの墓地にある`],
    [/^(.+?) (?:is|are) in your hand$/, x => np(x) && `${np(x)}があなたの手札にある`],
    [/^Gain life$/, () => 'ライフを得る'],
    [/^Gain life in any way$/, () => '何らかの方法でライフを得る'],
    [/^Gain any amount of life$/, () => '任意の量のライフを得る'],
    [/^Repeat steps? (\d+) and (\d+) once$/, (a, b) => `手順${a}と${b}をもう一度繰り返す`],
    [/^Repeat step (\d+) as desired$/, n => `必要なだけ手順${n}を繰り返す`],
    [/^(.+?) is paired with (.+)$/, (x, y) => np(x) && np(y) && `${np(x)}と${np(y)}が組になっている`],
    [/^An opponent cannot block (.+)$/, x => np(x) && `対戦相手は${np(x)}をブロックできない`],
    [/^An opponent cannot block and kill creatures you control$/, () => '対戦相手はあなたのクリーチャーをブロックして倒せない'],
    [/^You control (?:a|another) creature with power (\d+) or greater$/, n => `あなたはパワーが${n}以上の他のクリーチャーをコントロールしている`],
    [/^You control a (?:permanent|land) that can tap to produce at least (\{.+\})$/, x => `あなたはタップして少なくとも${x}を出せるパーマネントをコントロールしている`],
    [/^(.+?) has "(.+)" chosen$/, (x, y) => np(x) && `${np(x)}で「${y}」が選ばれている`],
    [/^(.+?) dies, triggering itself and (.+)$/, (x, y) => np(x) && np(y) && `${np(x)}が死亡し、それ自身と${np(y)}が誘発する`],
    [/^It (?:will not|won't) enter with a finality counter on it due to (.+)$/, r => (np(r) || reasonNp(r)) && `${np(r) || reasonNp(r)}により、終局カウンターが置かれずに戦場に出る`],
    [/^Repeat from step (\d+) (two|three|four) additional times$/, (n, k) => `手順${n}からさらに${num(k)}回繰り返す`],
    [/^Repeat from step (\d+) each (combat phase|turn)$/, (n, x) => `${{ 'combat phase': '戦闘フェイズ', turn: 'ターン' }[x]}ごとに手順${n}から繰り返す`],
    [/^Repeat (?:an arbitrarily large|any) number of times$/, () => '好きな回数だけ繰り返す'],
    [/^You control a creature with power (\d+) or greater$/, n => `あなたはパワーが${n}以上のクリーチャーをコントロールしている`],
    [/^(.+?) has power (\d+) or greater$/, (x, n) => np(x) && `${np(x)}のパワーが${n}以上である`],
    [/^You control (one|two|three|four|five|six|seven|\d+) or more (.+)$/, (n, x) => bare(x) && `あなたは${bare(x)}を${num(n)}${unit(x)}以上コントロールしている`],
    [/^You control (?:at least )?(one|two|three|four|five|six|seven|\d+) (.+?)$/, (n, x) => bare(x) && `あなたは${bare(x)}を${num(n)}${unit(x)}以上コントロールしている`],
    [/^You have max speed$/, () => 'あなたのスピードが最高である'],
    [/^You have at least (one|two|three|\d+) cards? in (?:your )?hand$/, n => `手札にカードが${num(n)}枚以上ある`],
    [/^You've cast a spell this turn$/, () => 'このターン、あなたは呪文を唱えている'],
    [/^(.+?) (?:is )?exiled (?:by|with) (.+)$/, (x, y) => np(x) && np(y) && `${np(x)}が${np(y)}によって追放されている`],
    [/^(.+?) (?:is )?on the battlefield as a copy of (.+)$/, (x, y) => np(x) && np(y) && `${np(x)}が${np(y)}のコピーとして戦場にある`],
    [/^(.+?) has at least (one|two|three|four|five|\d+) ([+-]\d+\/[+-]\d+|charge|loyalty|energy|oil|time|lore) counters? on it$/, (x, n, c) => np(x) && counter(c) && `${np(x)}に${counter(c)}が${num(n)}個以上置かれている`],
    [/^It will not have a ([+-]\d+\/[+-]\d+) counter on it due to (.+)$/, (c, r) => reasonNp(r) && `${reasonNp(r)}により、それには${c}カウンターが置かれない`],
    [/^Choose to return (.+?) to the command zone from your graveyard$/, x => np(x) && `${np(x)}を墓地から統率領域に戻すことを選ぶ`],
    [/^"(.+)" chosen with (.+)$/, (x, y) => np(y) && `${np(y)}で「${x}」が選ばれている`],
    [/^Move to your next turn, drawing (.+?) during your draw step$/, x => np(x) && `あなたの次のターンに移り、ドロー・ステップに${np(x)}を引く`],
    [/^There is a land card in your library that can be fetched using (.+)$/, x => np(x) && `ライブラリーに${np(x)}で探せる土地カードがある`],
    [/^You have a way to give (.+?) (indestructible|haste|hexproof|flying)$/, (x, k) => np(x) && `${np(x)}に${KW[k]}を与える手段がある`],
    [/^You control a creature that has not been tapped this turn$/, () => 'このターンにタップされていないクリーチャーをコントロールしている'],
    [/^(.+?) (?:does not|doesn't) have (?:a|any) ([+-]\d+\/[+-]\d+) counters? on it$/, (x, c) => np(x) && `${np(x)}に${c}カウンターが置かれていない`],
    [/^Draw a card$/, () => 'カードを1枚引く'],
    [/^Move to your next turn$/, () => 'あなたの次のターンに移る'],
    [/^Repeat$/, () => '繰り返す'],
    [/^Repeat from step (\d+)(?: one additional time)?$/, (n) => `手順${n}から繰り返す`],
    [/^Repeat steps? (\d+)(?: (?:and|-|to|through) (\d+))?(?: one additional time)?$/, (a, b) => b ? `手順${a}〜${b}を繰り返す` : `手順${a}を繰り返す`],
    [/^Repeat each (combat phase|turn|upkeep|end step)$/, x => `${{ 'combat phase': '戦闘フェイズ', turn: 'ターン', upkeep: 'アップキープ', 'end step': '終了ステップ' }[x]}ごとに繰り返す`],
    [/^Repeat any number of times$/, () => '好きな回数だけ繰り返す'],
    [/^Repeat step (\d+) until you have enough mana to cast (.+)$/, (n, x) => np(x) && `${np(x)}を唱えられるだけのマナが揃うまで手順${n}を繰り返す`],
    [/^Repeat step (\d+) until you control no lands$/, n => `土地をコントロールしなくなるまで手順${n}を繰り返す`],
  ];
  function main(s) {
    let m;
    // several sentences in one line
    const parts = s.split(/\. (?=[A-Z«])/);
    if (parts.length > 1) { const p = parts.map(sentence); return p.every(Boolean) ? p.join('。') : null; }
    for (const [re, fn] of STATES) { if ((m = s.match(re))) { const r = fn(...m.slice(1)); if (r) return r; } }
    // Resolve …
    if ((m = s.match(/^Resolve the copy of («\d+»)'s ability(?:, (.+))?$/))) return withTail(`${m[1]}の能力のコピーを解決する`, m[2]);
    if ((m = s.match(/^Resolve (?:the |an? )(second |first )?(«\d+») trigger(?: from step (\d+))?(?:, (.+))?$/))) return withTail(`${m[3] ? `手順${m[3]}の` : ''}${m[1] ? ORD[m[1].trim()] : ''}${m[2]}の誘発型能力を解決する`, m[4]);
    if ((m = s.match(/^Resolve (the [a-z ]+?|the («\d+»)|the first trigger|the second trigger|the (?:first|second) («\d+») trigger|the persist creature's trigger)(?: from step (\d+))?(?:, (.+))?$/)) && np(m[1])) {
      return withTail(`${m[4] ? `手順${m[4]}の` : ''}${np(m[1])}を解決する`, m[5]);
    }
    if ((m = s.match(/^Resolve (?:the |both |all )?(.+?) (ability|abilities|trigger|triggers|copy|spell)(?: from step (\d+))?(?:, (.+))?$/))) {
      const x = m[1] === 'undying' ? '不死' : m[1] === 'persist' ? '頑強' : m[1] === 'modular' ? '接合' : m[1] === 'first «0»' ? '最初の«0»' : (m[1].startsWith('first ') ? null : np(m[1]));
      if (!x) return null;
      const kind = { ability: 'の能力', abilities: 'の能力', trigger: 'の誘発型能力', triggers: 'の誘発型能力', copy: 'のコピー', spell: 'の呪文' }[m[2]];
      const head = `${m[3] ? `手順${m[3]}の` : ''}${x}${kind}を解決する`;
      return withTail(head, m[4]);
    }
    if ((m = s.match(/^Resolve (.+?)(?:, (.+))?$/))) { const x = np(m[1]); return x && withTail(`${x}を解決する`, m[2]); }
    // Activate …
    if ((m = s.match(/^Activate (.+?)(?: (twice|again|three times))? by (.+?)(?:, (.+))?$/))) {
      const who = abilityOf(m[1]); let by = byPart(m[3]);
      if (!who || !by) return null;
      const times = { twice: '2回', again: 'もう一度', 'three times': '3回' }[m[2]] || '';
      let head;
      if (/(^|、)それら?(を|から)/.test(by)) {
        by = by.replace(/(^|、)それら?(を|から)/, `$1${who.owner}$2`);
        head = `${by}${who.label ? who.label + 'を' : ''}${times}起動する`;
      } else head = `${by}${who.owner}${who.label ? 'の' + who.label : ''}を${times}起動する`;
      return withTail(head, m[4]);
    }
    // Cast / Play …
    if ((m = s.match(/^(Cast|Play) (.+?)(?: from (your graveyard|exile|the top of your library|your hand|the command zone))?(?: for its (\w+) cost)?(?: by paying (.+?))?(?: due to (.+?))?(?:, (.+))?$/))) {
      const x = np(m[2]); if (!x) return null;
      const from = m[3] ? zone(m[3]) + 'から' : '';
      const p = m[5] ? payment(m[5]) : '';
      if (m[5] && !p) return null;
      const why = m[6] ? (np(m[6]) || reasonNp(m[6])) : '';
      if (m[6] && !why) return null;
      const alt = m[4] ? `${{ escape: '脱出', flashback: 'フラッシュバック', unearth: '蘇生', disturb: '降霊' }[m[4]] || m[4]}コストで` : '';
      const head = `${p ? p + 'を支払って' : ''}${from}${alt}${x}を${m[1] === 'Cast' ? '唱える' : 'プレイする'}${why ? `（${why}により）` : ''}`;
      return withTail(head, m[7]);
    }
    if ((m = s.match(/^Play a land$/))) return '土地を1つプレイする';
    if ((m = s.match(/^Cast (.+?) either from your hand or from the (command zone|top of your library) by paying (.+?)(?: plus commander tax,? if applicable)?$/))) {
      const x = np(m[1]), p = payment(m[3]); return x && p && `${p}${/commander tax/.test(s) ? 'と統率者税' : ''}を支払って手札か${m[2] === 'command zone' ? '統率領域' : 'ライブラリーの一番上'}から${x}を唱える`;
    }
    if ((m = s.match(/^Cast (.+?) by paying (.+?) and removing a counter from (.+)$/))) { const x = np(m[1]), p = payment(m[2]), y = np(m[3]); return x && p && y && `${p}を支払い、${y}からカウンターを1個取り除いて${x}を唱える`; }
    if ((m = s.match(/^Cast (.+?) from the top of your library by paying (.+?) and removing a counter from (.+)$/))) { const x = np(m[1]), p = payment(m[2]), y = np(m[3]); return x && p && y && `${p}を支払い、${y}からカウンターを1個取り除いて、ライブラリーの一番上から${x}を唱える`; }
    if ((m = s.match(/^Cast (.+?) by paying its mana cost, which is reduced by (.+)$/))) { const x = np(m[1]), y = np(m[2]); return x && y && `${y}で軽減されたマナ・コストを支払って${x}を唱える`; }
    if ((m = s.match(/^Cast (.+?) with buyback by paying (.+)$/))) { const x = np(m[1]), p = payment(m[2]); return x && p && `${p}を支払ってバイバック付きで${x}を唱える`; }
    if ((m = s.match(/^Cast (.+?) either from your hand or from the command zone by paying (.+)$/))) { const x = np(m[1]), p = payment(m[2]); return x && p && `${p}を支払って手札か統率領域から${x}を唱える`; }
    if ((m = s.match(/^Cast (.+?) for its (\w+) cost by paying (.+?) and exiling (.+?) from your graveyard(?:, (.+))?$/))) {
      const x = np(m[1]), p = payment(m[3]), e = np(m[4]); if (!x || !p || !e) return null;
      return withTail(`${p}を支払い、墓地から${e}を追放して${{ escape: '脱出', delve: '探査' }[m[2]] || m[2]}で${x}を唱える`, m[5]);
    }
    // triggers
    if ((m = s.match(/^When (.+?) (dies|enters untapped|enters(?: the battlefield)?|enter|attacks|leaves the battlefield|is put into (?:a|your) graveyard from the battlefield|becomes tapped|deals combat damage to a player)(?: as (?:an? )?(.+?) due to (.+?))?, (.+)$/))) {
      const x = np(m[1]); if (!x) return null;
      const ev = { dies: 'が死亡したとき', enters: 'が戦場に出たとき', 'enters the battlefield': 'が戦場に出たとき', 'enters untapped': 'がアンタップ状態で戦場に出たとき', 'enter': 'が戦場に出たとき', attacks: 'が攻撃したとき', 'leaves the battlefield': 'が戦場を離れたとき',
        'becomes tapped': 'がタップ状態になったとき', 'deals combat damage to a player': 'がプレイヤーに戦闘ダメージを与えたとき' }[m[2]] || 'が戦場から墓地に置かれたとき';
      let as = '';
      if (m[3]) {
        const kindJa = { enchantment: 'エンチャント', artifact: 'アーティファクト', land: '土地', creature: 'クリーチャー', copy: 'コピー' }[m[3]] || TYPES[m[3]] || null;
        const why = np(m[4]) || reasonNp(m[4]);
        if (!kindJa || !why) return null;
        as = `（${why}により${kindJa}として）`;
      }
      const rest = trig(m[5]); return rest && `${x}${as}${ev}、${rest}`;
    }
    if ((m = s.match(/^At the end of (?:your )?combat(?: phase)?, (.+)$/))) { const r = trig(m[1]) || main(m[1]); return r && `戦闘の終了時に、${r}`; }
    if ((m = s.match(/^At the beginning of (your|your next|each|the next) (upkeep|end step|combat|draw step|turn)(?: of each opponent)?, (.+)$/))) {
      const when = `${{ your: 'あなたの', 'your next': 'あなたの次の', each: '各', 'the next': '次の' }[m[1]]}${{ upkeep: 'アップキープ', 'end step': '終了ステップ', combat: '戦闘', 'draw step': 'ドロー・ステップ', turn: 'ターン' }[m[2]]}の開始時に、`;
      const r = trig(m[3]) || main(m[3]); return r && when + r;
    }
    if ((m = s.match(/^In response to (.+?), (.+)$/))) { const x = np(m[1]); const r = sentence(m[2].charAt(0).toUpperCase() + m[2].slice(1)); return x && r && `${x}に対応して、${r}`; }
    if ((m = s.match(/^(.+?) enters the battlefield, (?!triggering)(.+)$/))) { const x = np(m[1]), t = vp(m[2]); return x && t && `${x}が戦場に出て、${t}`; }
    if ((m = s.match(/^(.+?) enters the battlefield, triggering (.+)$/))) { const x = np(m[1]), y = np(m[2]); return x && y && `${x}が戦場に出て、${y}が誘発する`; }
    if ((m = s.match(/^(.+?) leaves the battlefield, (.+)$/))) { const x = np(m[1]); const t = vp(m[2]); return x && t && `${x}が戦場を離れ、${t}`; }
    const tr = trig(s); if (tr) return tr;
    if ((m = s.match(/^(.+?) dies as a state-based action due to having (?:zero|0) toughness$/)) && np(m[1])) return `${np(m[1])}はタフネスが0なので状態起因処理で死亡する`;
    if ((m = s.match(/^(.+?) dies, triggering (.+?)(?:, (.+))?$/)) && np(m[1]) && (trigSubject(m[2]) || np(m[2]))) {
      const r = withTail(`${np(m[1])}が死亡し、${trigSubject(m[2]) || np(m[2])}が誘発する`, m[3]); if (r) return r;
    }
    if ((m = s.match(/^(.+?) dies$/)) && np(m[1])) return `${np(m[1])}が死亡する`;
    if ((m = s.match(/^Sacrifice (.+?) to (.+?)(?: for (\{[^ ]+\}))?(?:(?:,| to) (add(?:ing)? .+))?$/)) && np(m[1]) && np(m[2])) {
      const head = `${m[3] ? m[3] + 'を支払い、' : ''}${np(m[2])}のコストとして${np(m[1])}を生け贄に捧げる`;
      const r = m[4] ? withTail(head, m[4].replace(/^add /, 'adding ')) : head; if (r) return r;
    }
    if ((m = s.match(/^(.+?) (?:is |are )?on the battlefield$/)) && np(m[1])) return `${np(m[1])}が戦場にある`;
    // other actions
    if ((m = s.match(/^Deal combat damage(?: to (an opponent|a player|each opponent))? using (.+?)(?:, (.+))?$/))) {
      const x = attackerNp(m[2]); if (!x) return null;
      return withTail(`${x}で${m[1] ? np(m[1]) + 'に' : ''}戦闘ダメージを与える`, m[3]);
    }
    if ((m = s.match(/^Declare (.+?) as attackers, (.+)$/))) { const x = attackerNp(m[1]); const t = vp(m[2]); return x && t && `${x}で攻撃し、${t}`; }
    if ((m = s.match(/^Declare (.+?) as (?:an )?attackers?$/))) { const x = attackerNp(m[1]); return x && `${x}で攻撃する`; }
    if ((m = s.match(/^Put (.+?) into your graveyard due to the legend rule$/))) { const x = np(m[1]); return x && `レジェンド・ルールにより${x}を墓地に置く`; }
    if ((m = s.match(/^If you control two or more (.+?) tokens, put all but one into your graveyard due to the legend rule$/))) return 'レジェンド・ルールにより、同じ名前のトークンを1つ残して墓地に置く';
    if ((m = s.match(/^Animate (.+?) using (.+)$/))) { const x = np(m[1]), y = np(m[2]); return x && y && `${y}で${x}をクリーチャー化する`; }
    if ((m = s.match(/^Cause (.+?) to become an? (artifact|creature|land) using (.+)$/))) { const x = np(m[1]), y = np(m[3]); return x && y && `${y}で${x}を${{ artifact: 'アーティファクト', creature: 'クリーチャー', land: '土地' }[m[2]]}にする`; }
    if ((m = s.match(/^Fetch a land using (.+)$/))) { const x = np(m[1]); return x && `${x}で土地を1つ探す`; }
    if ((m = s.match(/^Put (.+?) onto the battlefield$/))) { const x = np(m[1]); return x && `${x}を戦場に出す`; }
    const v = vp(s.charAt(0).toLowerCase() + s.slice(1)); if (v) return v;
    return null;
  }
  function attackerNp(s) {
    let m;
    if ((m = s.match(/^the creature (?:that has|with) (.+?) attached(?: and (.+))?$/))) {
      const x = np(m[1]); if (!x) return null;
      const base = `${x}がつけられたクリーチャー`;
      if (m[2]) { const y = np(m[2]); return y && `${base}と${y}`; }
      return base;
    }
    return np(s);
  }
  // "«0» triggers, …" / "«0» and «1» trigger" / "its persist ability triggers, …"
  function trig(s) {
    let m;
    if ((m = s.match(/^(.+?) (?:each )?triggers?(?: twice)?(?: due to (.+?))?(?:, (.+))?$/))) {
      const who = trigSubject(m[1]); if (!who) return null;
      const twice = / triggers? twice/.test(s) ? '2回' : '';
      const why = m[2] ? (np(m[2]) || reasonNp(m[2])) : '';
      if (m[2] && !why) return null;
      const head = `${who}が${twice}誘発する${why ? `（${why}により）` : ''}`;
      return withTail(head, m[3]);
    }
    return null;
  }
  function trigSubject(s) {
    let m;
    if (s === 'it') return 'それ';
    if ((m = s.match(/^(?:its|the) (persist|undying|modular|fabricate|soulbond|earthbend|first|second|third|evolve|exploit|landfall) (?:ability|abilities)(?: and (?:its )?(persist|undying|modular) ability)?$/))) {
      const name = { persist: '頑強', undying: '不死', modular: '接合', fabricate: '製造', soulbond: '結魂', earthbend: '土変化', first: '1つ目の', second: '2つ目の', third: '3つ目の', evolve: '進化', exploit: '濫用', landfall: '上陸' };
      return `その${name[m[1]]}${/first|second|third/.test(m[1]) ? '能力' : '能力'}${m[2] ? `と${name[m[2]]}能力` : ''}`;
    }
    if ((m = s.match(/^(.+?)'s (first|second|third) ability$/))) { const x = np(m[1]); return x && `${x}の${ORD[m[2]]}能力`; }
    if ((m = s.match(/^(.+?), (.+?),? and the undying creature's undying ability$/))) { const x = np(m[1]), y = np(m[2]); return x && y && `${x}と${y}と不死を持つクリーチャーの不死能力`; }
    if ((m = s.match(/^it(?:, (.+?))?,? and (.+)$/))) { const items = [m[1], m[2]].filter(Boolean).map(np); return items.every(Boolean) ? ['それ', ...items].join('と') : null; }
    return np(s);
  }

  // ---------------------------------------------------------------- results and card kinds
  const RESULT_TAIL = {
    'creature ETB': 'クリーチャーのETB（戦場に出る誘発）', 'creature LTB': 'クリーチャーのLTB（戦場を離れる誘発）', 'death triggers': '死亡誘発',
    'creature sacrifice triggers': 'クリーチャーの生け贄誘発', 'storm count': 'ストーム・カウント', 'colored mana': '色マナ', 'artifact ETB': 'アーティファクトのETB',
    '+1/+1 counters on a creature': 'クリーチャー1体への+1/+1カウンター', 'draw triggers': 'ドロー誘発', 'artifact LTB': 'アーティファクトのLTB',
    'creature tokens': 'クリーチャー・トークン', 'lifegain triggers': 'ライフ獲得誘発', 'landfall triggers': '上陸誘発', 'card draw': 'ドロー',
    'artifact sacrifice triggers': 'アーティファクトの生け贄誘発', 'colorless mana': '無色マナ', 'lifegain': 'ライフ獲得', 'magecraft triggers': '魔技誘発',
    'damage': 'ダメージ', 'mana': 'マナ', 'artifact tokens': 'アーティファクト・トークン', 'mana creatures you control can produce': 'マナ（あなたのクリーチャーが出せる色）',
    'turns': 'ターン', 'self-mill': '自分のライブラリーの切削', 'untap of creatures you control': 'あなたのクリーチャーのアンタップ', 'tapped creature tokens': 'タップ状態のクリーチャー・トークン',
    '+1/+1 counters on creatures you control': 'あなたのクリーチャーへの+1/+1カウンター', 'self-discard triggers': '自分の手札を捨てる誘発', 'combat phases': '戦闘フェイズ',
    'creature tokens with haste': '速攻を持つクリーチャー・トークン', 'lifeloss': 'ライフ損失', 'scry 1': '占術1', 'mana lands you control can produce': 'マナ（あなたの土地が出せる色）',
    'Treasure tokens': '宝物・トークン', 'red mana': '赤マナ', 'green mana': '緑マナ', 'black mana': '黒マナ', 'blue mana': '青マナ', 'white mana': '白マナ',
    'combat damage': '戦闘ダメージ', 'mill': '切削', 'blinking': '明滅', 'untap of lands you control': 'あなたの土地のアンタップ', 'surveil': '諜報', 'looting': 'ルーター（引いて捨てる）',
    'Blood tokens': '血・トークン', 'rummaging': '物色（捨てて引く）', 'charge counters on a permanent': 'パーマネントへの蓄積カウンター', 'untap of creatures': 'クリーチャーのアンタップ',
    'untap of artifact creatures you control': 'あなたのアーティファクト・クリーチャーのアンタップ', 'tapped Forest tokens': 'タップ状態の森・トークン',
    'mana permanents you control can produce': 'マナ（あなたのパーマネントが出せる色）', 'blinking of nonland permanents': '土地でないパーマネントの明滅', 'proliferate': '増殖',
    'lifeloss for all players': '全プレイヤーのライフ損失', '+1/+1 counters on certain creatures': '特定のクリーチャーへの+1/+1カウンター', 'Clue tokens': '手掛かり・トークン',
    'Food tokens': '食物・トークン', 'commander casts': '統率者の唱え直し', 'recursion of creature cards in your graveyard': '墓地のクリーチャー・カードの再利用',
    'untap of artifacts you control': 'あなたのアーティファクトのアンタップ', 'energy counters': 'エネルギー・カウンター', 'mana artifacts you control can produce': 'マナ（あなたのアーティファクトが出せる色）',
    '+1/+1 counters on most creatures you control': 'あなたのほとんどのクリーチャーへの+1/+1カウンター', 'tapped Island tokens': 'タップ状態の島・トークン',
    'draw triggers for any number of opponents': '好きな数の対戦相手のドロー誘発', 'tapped Mountain tokens': 'タップ状態の山・トークン', 'tapped Plains tokens': 'タップ状態の平地・トークン',
    'tapped Swamp tokens': 'タップ状態の沼・トークン', 'tapped copies of a specific land': '特定の土地のタップ状態のコピー', 'blinking of some creatures': '一部のクリーチャーの明滅',
    'blinking of permanents': 'パーマネントの明滅', 'card draw for any number of players': '好きな数のプレイヤーのドロー', 'damage to one opponent': '対戦相手1人へのダメージ',
    '+1/+1 counters': '+1/+1カウンター', 'mana nontoken creatures you control can produce': 'マナ（トークンでないあなたのクリーチャーが出せる色）',
    'creature copies of artifacts you control': 'あなたのアーティファクトのクリーチャー・コピー', 'tapped Treasure tokens': 'タップ状態の宝物・トークン', 'blinking of most creatures': 'ほとんどのクリーチャーの明滅',
    'proliferate for permanents': 'パーマネントへの増殖', 'Forest tokens': '森・トークン', 'untap of permanents you control': 'あなたのパーマネントのアンタップ', 'Mutagen tokens': 'ミュータジェン・トークン',
    'card draw for any number of opponents': '好きな数の対戦相手のドロー', 'tapped Food tokens': 'タップ状態の食物・トークン', 'ventures into the dungeon': 'ダンジョン探索',
    '-1/-1 counters': '-1/-1カウンター', 'untap of basic lands you control': 'あなたの基本土地のアンタップ', 'mana among colors with which you have devotion': 'マナ（信心のある色）',
    'untap of all creatures': 'すべてのクリーチャーのアンタップ', 'untap of some creatures you control': 'あなたの一部のクリーチャーのアンタップ', '+1/+1 counters on Golems you control': 'あなたのゴーレムへの+1/+1カウンター',
    'mana basic lands you control can produce': 'マナ（あなたの基本土地が出せる色）', 'copies of artifacts you control': 'あなたのアーティファクトのコピー', 'draw triggers for all players': '全プレイヤーのドロー誘発',
    'tapped Clue tokens': 'タップ状態の手掛かり・トークン', 'Island tokens': '島・トークン', 'lifeloss for target opponent': '対戦相手1人のライフ損失', 'card draw for all players': '全プレイヤーのドロー',
    'copies of a specific artifact': '特定のアーティファクトのコピー', 'card draw for target opponent': '対戦相手1人のドロー', 'draw triggers for target opponent': '対戦相手1人のドロー誘発',
    'untap of nontoken artifacts you control': 'トークンでないあなたのアーティファクトのアンタップ', 'tapped artifact tokens': 'タップ状態のアーティファクト・トークン',
    'copies of creature tokens you control': 'あなたのクリーチャー・トークンのコピー', 'scry': '占術', 'copies of creatures you control': 'あなたのクリーチャーのコピー', 'copies of a specific land': '特定の土地のコピー',
    'Plains tokens': '平地・トークン', 'Mountain tokens': '山・トークン', 'Swamp tokens': '沼・トークン', 'Map tokens': '地図・トークン', 'Rock tokens': '岩・トークン', 'Lotus tokens': '蓮・トークン',
    'Munitions tokens': '弾薬・トークン', 'experience counters': '経験カウンター', 'death triggers for target opponent': '対戦相手1人の死亡誘発', 'creature LTB for target opponent': '対戦相手1人のクリーチャーのLTB',
    'creature ETB for target opponent': '対戦相手1人のクリーチャーのETB', 'mill for target opponent': '対戦相手1人の切削', 'creature tokens for target opponent': '対戦相手1人のクリーチャー・トークン',
    'damage to all players': '全プレイヤーへのダメージ', 'damage to creatures': 'クリーチャーへのダメージ', 'combat damage to one opponent': '対戦相手1人への戦闘ダメージ',
    'Gold tokens': '金・トークン', 'planeswalker activations': 'プレインズウォーカーの起動', 'tapped creature tokens with haste': '速攻を持つタップ状態のクリーチャー・トークン',
    'tapped land tokens': 'タップ状態の土地・トークン', 'tapped Powerstone tokens': 'タップ状態のパワーストーン・トークン', 'tapped Rock tokens': 'タップ状態の岩・トークン',
    'tapped Shard tokens': 'タップ状態の欠片・トークン', 'tapped Heartwood tokens': 'タップ状態の心材・トークン', 'tapped Munitions tokens': 'タップ状態の弾薬・トークン',
    'copies of all permanents': 'すべてのパーマネントのコピー', 'copies of all artifacts': 'すべてのアーティファクトのコピー', 'copies of all creatures': 'すべてのクリーチャーのコピー',
    'copies of permanents you control': 'あなたのパーマネントのコピー', 'copies of a specific creature': '特定のクリーチャーのコピー', 'copies of a specific planeswalker': '特定のプレインズウォーカーのコピー',
    'copies of a specific enchantment': '特定のエンチャントのコピー', 'casts of a specific spell': '特定の呪文の唱え直し', 'self-discard triggers for any number of players': '好きな数のプレイヤーの手札を捨てる誘発',
    'looting for any number of players': '好きな数のプレイヤーのルーター', 'card draw for opponents': '対戦相手のドロー', 'draw triggers for each opponent': '各対戦相手のドロー誘発',
    'creature tokens for all players': '全プレイヤーのクリーチャー・トークン', 'untap of nontoken creatures you control': 'トークンでないあなたのクリーチャーのアンタップ',
    'untap of most creatures you control': 'あなたのほとんどのクリーチャーのアンタップ', 'untap of nonland permanents you control': 'あなたの土地でないパーマネントのアンタップ',
    'untap of noncreature artifacts you control': 'あなたのクリーチャーでないアーティファクトのアンタップ', 'recursion of creatures you control': 'あなたのクリーチャーの再利用',
    'recursion of artifacts you control': 'あなたのアーティファクトの再利用', 'blinking of nonland permanents you control': 'あなたの土地でないパーマネントの明滅',
  };
  const RESULT_FULL = {
    'Win the game': 'ゲームに勝利する', 'Lock': 'ロック', 'Exile your library': 'ライブラリーを追放する', 'Target opponent loses the game': '対戦相手1人がゲームに敗北する',
    'Each opponent loses the game': '各対戦相手がゲームに敗北する', 'Mass Land Denial': '土地の全体除去（土地破壊）', 'Skip your draw steps': 'ドロー・ステップを飛ばす',
    'Draw the game': 'ゲームを引き分けにする', 'Destroy all creatures opponents control': '対戦相手のクリーチャーをすべて破壊する', 'Infinitely large creature until end of turn': 'ターン終了時まで無限に大きいクリーチャー',
    'Near-infinitely large creature until end of turn': 'ターン終了時までほぼ無限に大きいクリーチャー', 'Infinitely large creatures you control until end of turn': 'ターン終了時まで無限に大きいあなたのクリーチャー',
    'Infinitely powerful creature until end of turn': 'ターン終了時までパワーが無限のクリーチャー', 'Infinitely large creature': '無限に大きいクリーチャー', 'Near-infinitely large creature': 'ほぼ無限に大きいクリーチャー',
    'Win the game at the beginning of your next upkeep': '次のアップキープの開始時にゲームに勝利する', 'Put all creature cards from your library onto the battlefield': 'ライブラリーのクリーチャー・カードをすべて戦場に出す',
    'Put all creature cards from your library onto the battlefield tapped': 'ライブラリーのクリーチャー・カードをすべてタップ状態で戦場に出す',
    'Exile your library with the ability to play the exiled cards until your next end step': 'ライブラリーを追放し、次の終了ステップまでそれらをプレイできる',
    'Return all creature cards from all graveyards to the battlefield under your control': 'すべての墓地のクリーチャー・カードをあなたのコントロール下で戦場に戻す',
    'Infinitely powerful creatures you control until end of turn': 'ターン終了時までパワーが無限のあなたのクリーチャー', 'Prevent all damage that would be dealt to you': 'あなたに与えられるダメージをすべて軽減する',
    'Counter all spells opponents cast': '対戦相手の呪文をすべて打ち消す', 'Exile each opponent\'s library': '各対戦相手のライブラリーを追放する', 'You have protection from everything': 'あなたはすべてに対するプロテクションを持つ',
    "You can't be attacked": 'あなたは攻撃されない', 'Exile all permanents': 'すべてのパーマネントを追放する', 'Cast all spells in your library': 'ライブラリーの呪文をすべて唱える',
    'Players can\'t draw cards': 'プレイヤーはカードを引けない', 'Opponents can\'t cast spells': '対戦相手は呪文を唱えられない', 'Creatures can\'t attack': 'クリーチャーは攻撃できない',
    'Destroy any number of creatures': '好きな数のクリーチャーを破壊する', 'Destroy any number of nonland permanents': '好きな数の土地でないパーマネントを破壊する',
    'Return all lands you control to your hand': 'あなたの土地をすべて手札に戻す', 'Target player loses the game': 'プレイヤー1人がゲームに敗北する', 'Manifest your entire library': 'ライブラリーをすべて予示する',
    'Arrange your library in any order': 'ライブラリーを好きな順番に並べる', 'Exile all creatures opponents control': '対戦相手のクリーチャーをすべて追放する',
    'Exile all nonland permanents opponents control': '対戦相手の土地でないパーマネントをすべて追放する', 'Destroy all lands opponents control': '対戦相手の土地をすべて破壊する',
    'Each opponent sacrifices all creatures they control': '各対戦相手はクリーチャーをすべて生け贄に捧げる', 'Opponents skip their untap steps': '対戦相手はアンタップ・ステップを飛ばす',
    'Gain control of all creatures': 'すべてのクリーチャーのコントロールを得る', 'Return all creature cards from your graveyard to the battlefield': '墓地のクリーチャー・カードをすべて戦場に戻す',
    'Return all creature cards from your graveyard to your hand': '墓地のクリーチャー・カードをすべて手札に戻す', 'Return all cards from your graveyard to your hand': '墓地のカードをすべて手札に戻す',
    'Return all instant and sorcery cards from your graveyard to your hand': '墓地のインスタントとソーサリー・カードをすべて手札に戻す',
    'Return all nonland permanents from your graveyard to the battlefield': '墓地の土地でないパーマネント・カードをすべて戦場に戻す',
    'Put all basic lands from your library into your hand': 'ライブラリーの基本土地をすべて手札に加える', 'Put all basic lands from your library onto the battlefield tapped': 'ライブラリーの基本土地をすべてタップ状態で戦場に出す',
    'Put all basic lands from your library onto the battlefield': 'ライブラリーの基本土地をすべて戦場に出す', 'Put all lands from your library onto the battlefield tapped': 'ライブラリーの土地をすべてタップ状態で戦場に出す',
    'Put all lands from your library onto the battlefield': 'ライブラリーの土地をすべて戦場に出す', 'Put all creature cards from your library into your hand': 'ライブラリーのクリーチャー・カードをすべて手札に加える',
    'Return any number of creatures to their owners\' hands': '好きな数のクリーチャーをオーナーの手札に戻す', 'Return any number of permanents to their owner\'s hand': '好きな数のパーマネントをオーナーの手札に戻す',
    'Destroy all permanents opponents control each turn': '毎ターン、対戦相手のパーマネントをすべて破壊する', 'Each opponent sacrifices nearly infinite creatures': '各対戦相手はほぼ無限のクリーチャーを生け贄に捧げる',
  };
  Object.assign(RESULT_TAIL, {
    'mana lands you control that enter the battlefield untapped can produce': 'マナ（アンタップ状態で戦場に出るあなたの土地が出せる色）', 'card draw at the beginning of the next upkeep': '次のアップキープの開始時のドロー',
    'mana permanents you control that enter the battlefield untapped can produce': 'マナ（アンタップ状態で戦場に出るあなたのパーマネントが出せる色）', 'draw triggers at the beginning of the next upkeep': '次のアップキープの開始時のドロー誘発',
    '+1/+1 counters on a creature token': 'クリーチャー・トークン1体への+1/+1カウンター', 'colorless mana that can only be spent to activate abilities': '無色マナ（能力の起動にのみ使える）',
    'draw triggers for any number of players': '好きな数のプレイヤーのドロー誘発', 'colored mana that can only be spent to cast your commander': '色マナ（統率者を唱えるためにのみ使える）',
    'power for certain creatures until end of turn': 'ターン終了時までの特定のクリーチャーのパワー', 'colored mana that can only be spent to activate abilities': '色マナ（能力の起動にのみ使える）',
    'copies of artifacts you control with haste': '速攻を持つあなたのアーティファクトのコピー', 'mana nontoken artifacts you control can produce': 'マナ（トークンでないあなたのアーティファクトが出せる色）',
    "colorless mana that can't be spent to cast spells from your hand": '無色マナ（手札から呪文を唱えるのには使えない）', 'mana of colors among permanents you control': 'マナ（あなたのパーマネントの色）',
    'power and toughness for most creatures you control until end of turn': 'ターン終了時までのあなたのほとんどのクリーチャーのパワーとタフネス', 'creature tokens that are infinitely large': '無限に大きいクリーチャー・トークン',
    'blue mana that can only be spent to cast instant and sorcery spells': '青マナ（インスタントとソーサリーを唱えるためにのみ使える）', 'red mana that can only be spent to cast instant and sorcery spells': '赤マナ（インスタントとソーサリーを唱えるためにのみ使える）',
    'mana legendary creatures you control can produce': 'マナ（あなたの伝説のクリーチャーが出せる色）', 'untap of legendary creatures you control': 'あなたの伝説のクリーチャーのアンタップ',
    'recursion of some creature cards in your graveyard': '墓地の一部のクリーチャー・カードの再利用', 'recursion of creature cards in all graveyards': 'すべての墓地のクリーチャー・カードの再利用',
    'colored mana that can only be spent to cast creature spells': '色マナ（クリーチャー呪文を唱えるためにのみ使える）', 'token copies of nonlegendary enchantments you control': 'あなたの伝説でないエンチャントのトークン・コピー',
    'copies of abilities you control on the stack': 'スタック上のあなたの能力のコピー', 'power and toughness for certain creatures until end of turn': 'ターン終了時までの特定のクリーチャーのパワーとタフネス',
    'copies of creatures you control with haste': '速攻を持つあなたのクリーチャーのコピー', 'mana artifact creatures you control can produce': 'マナ（あなたのアーティファクト・クリーチャーが出せる色）',
    "colorless mana that can't be spent to cast nonartifact spells": '無色マナ（アーティファクトでない呪文には使えない）', 'mana nonland permanents you control can produce': 'マナ（あなたの土地でないパーマネントが出せる色）',
    'untap of Samurai you control': 'あなたの侍のアンタップ', 'mana most artifacts you control can produce': 'マナ（あなたのほとんどのアーティファクトが出せる色）',
    '+1/+1 counters on an infinite number of creature tokens': '無限のクリーチャー・トークンへの+1/+1カウンター', 'copies of most creatures you control with haste': '速攻を持つあなたのほとんどのクリーチャーのコピー',
    'copies of instant and sorcery spells on the stack': 'スタック上のインスタントとソーサリーのコピー', 'recursion of Elemental cards in your graveyard': '墓地のエレメンタル・カードの再利用',
  });
  Object.assign(RESULT_FULL, {
    'Put all Equipment cards from your library onto the battlefield': 'ライブラリーの装備品カードをすべて戦場に出す', 'Put all land cards from your library and graveyard onto the battlefield': 'ライブラリーと墓地の土地カードをすべて戦場に出す',
    'Reduce the toughness of creatures opponents control to 0': '対戦相手のクリーチャーのタフネスを0にする', 'Put all lands with a basic land type from your library onto the battlefield tapped': 'ライブラリーの基本土地タイプを持つ土地をすべてタップ状態で戦場に出す',
    'Return most creature cards from your graveyard onto the battlefield': '墓地のほとんどのクリーチャー・カードを戦場に戻す', 'Put all artifact cards and a subset of creature cards from your library onto the battlefield': 'ライブラリーのアーティファクト・カードすべてと一部のクリーチャー・カードを戦場に出す',
    "Destroy each creature that enters the battlefield under an opponent's control": '対戦相手のコントロール下で戦場に出るクリーチャーをすべて破壊する', 'Exile your library with the ability to play the exiled cards until end of turn': 'ライブラリーを追放し、ターン終了時までそれらをプレイできる',
    'Target opponent returns all cards in their graveyard to their hand': '対戦相手1人は墓地のカードをすべて手札に戻す', "Return all permanents opponents control to their owner's hand": '対戦相手のパーマネントをすべてオーナーの手札に戻す',
    'Destroy all creatures opponents control whenever a creature enters the battlefield': 'クリーチャーが戦場に出るたび、対戦相手のクリーチャーをすべて破壊する', 'Put all lands from your hand and library onto the battlefield': '手札とライブラリーの土地をすべて戦場に出す',
    'Return some creature cards from your graveyard to the battlefield': '墓地の一部のクリーチャー・カードを戦場に戻す', 'Put all creature cards in your library onto the battlefield, then into your graveyard': 'ライブラリーのクリーチャー・カードをすべて戦場に出し、それから墓地に置く',
    'Cast a subset of spells in your library': 'ライブラリーの一部の呪文を唱える', "Cast any number of spells from opponents' libraries": '対戦相手のライブラリーから好きな数の呪文を唱える', 'Exile all cards in hands and graveyards': '手札と墓地のカードをすべて追放する',
    'Destroy all permanents opponents control on each of your turns': 'あなたのターンごとに対戦相手のパーマネントをすべて破壊する', 'Target player loses the game on each of your turns': 'あなたのターンごとにプレイヤー1人がゲームに敗北する',
  });
  function result(s) {
    if (RESULT_FULL[s]) return RESULT_FULL[s];
    let m;
    if ((m = s.match(/^(Infinite|Near-infinite) (.+)$/)) && RESULT_TAIL[m[2]]) return `${m[1] === 'Infinite' ? '無限の' : 'ほぼ無限の'}${RESULT_TAIL[m[2]]}`;
    if ((m = s.match(/^(\d+) (.+)$/))) { const r = result(m[2]); return r && `${r}×${m[1]}`; }
    return null;
  }
  const TEMPLATE = {
    'Persist Creature': '頑強を持つクリーチャー', 'Creature with Undying': '不死を持つクリーチャー', 'Undying Creature': '不死を持つクリーチャー',
    'Artifact Castable for Exactly {1}': 'ちょうど{1}で唱えられるアーティファクト', 'Creature Castable for One Colored Mana': '色マナ1点で唱えられるクリーチャー',
    'Artifact Castable for {0} that survives': '{0}で唱えられて戦場に残るアーティファクト', 'Haste Enabler': '速攻を与えるカード', 'Hero Creature': '英雄・クリーチャー',
    "Effects that Alter a Creature's Power/Toughness (Anthem Effects)": 'クリーチャーのパワー・タフネスを変える効果（全体強化）', 'Gives +1/+1 counter to creatures that enter': '戦場に出るクリーチャーに+1/+1カウンターを置くカード',
    'Increases +1/+1 Counter Placement but not -1/-1': '+1/+1カウンターを増やす（-1/-1は増やさない）カード', 'Permanent with Landfall Ability: Create Creature Token(s)': '上陸でクリーチャー・トークンを生成するパーマネント',
    'Creature with ETB: Earthbend': '戦場に出たとき土変化するクリーチャー', 'Zombie Creature': 'ゾンビ・クリーチャー', 'Creature that earthbends on entering': '戦場に出たとき土変化するクリーチャー',
    'Noncreature Artifact with MV<=1': 'マナ総量1以下のクリーチャーでないアーティファクト', 'Creature with Bloodthirst': '湧血を持つクリーチャー', 'Knight Creature with MV<=3': 'マナ総量3以下の騎士・クリーチャー',
    'Creature castable for {0} that survives': '{0}で唱えられて戦場に残るクリーチャー', 'Goblin, Orc or Army Creature Castable for One Colored Mana': '色マナ1点で唱えられるゴブリン・オーク・軍団クリーチャー',
    'Creature with Persist or Undying': '頑強か不死を持つクリーチャー', 'Changeling Creature': '多相を持つクリーチャー', 'Card Giving Creatures -1/-1': 'クリーチャーに-1/-1を与えるカード',
    'Zombie Creature castable for one colored mana': '色マナ1点で唱えられるゾンビ・クリーチャー', 'Card that Animates an Artifact': 'アーティファクトをクリーチャー化するカード',
    'Card That Animates a Land': '土地をクリーチャー化するカード', 'Dinosaur': '恐竜', 'One-drop creature with a second body': 'もう1体を残す1マナのクリーチャー',
    'Land with Cycling Cost that can be paid using one colored mana': '色マナ1点でサイクリングできる土地', 'Extra Turn Spell - GY on Resolution': '解決後に墓地に置かれる追加ターン呪文',
  };
  Object.assign(TEMPLATE, {
    'Card That Gives Lifelink': '絆魂を与えるカード', 'Land that adds at least two mana': 'マナを2点以上出せる土地', 'Nonlegendary Saga': '伝説でない英雄譚',
    'Artifact Creature with Mana Cost X and Toughness 0': 'マナ・コストがXでタフネス0のアーティファクト・クリーチャー', 'Creature with Mobilize': '動員を持つクリーチャー',
    'Card that Earthbends': '土変化するカード', 'Vehicle with MV >= 3 and a Crew Ability': '搭乗能力を持つマナ総量3以上の機体', 'Creature Castable for {0} that dies on enter': '{0}で唱えられて戦場に出てすぐ死亡するクリーチャー',
    'Artifact with MV<=2 that has a generic mana cost': '不特定マナ・コストのみのマナ総量2以下のアーティファクト', 'Cards Allowing a Creature to Tap for Free': 'クリーチャーを無償でタップさせるカード',
    'Card That Copies a Creature': 'クリーチャーをコピーするカード', 'Angel Creature': '天使・クリーチャー', 'Artifact Land': 'アーティファクト・土地', 'Spell with {X} in Mana Cost': 'マナ・コストに{X}を含む呪文',
    'Lhurgoyf Card with Base Power >= 1': '基本パワーが1以上のルアゴイフ・カード', 'Creature with MV=1 and Creates Creature Token(s) on Death': '死亡時にクリーチャー・トークンを生成するマナ総量1のクリーチャー',
    'Creature castable for {0}': '{0}で唱えられるクリーチャー', 'Villain Creature': '悪役クリーチャー', 'Creature with MV>=4 that has a generic mana cost': '不特定マナ・コストのみのマナ総量4以上のクリーチャー',
    'Legendary Creature with Flying and MV >= 4': '飛行を持つマナ総量4以上の伝説のクリーチャー', 'Card That Gives Indestructible': '破壊不能を与えるカード', 'Spell with Kicker or Multikicker': 'キッカーか多重キッカーを持つ呪文',
    'Artifact Creature that is a Gnome and/or Artificer': 'ノームか工匠のアーティファクト・クリーチャー', 'Green Nontoken Insect': '緑のトークンでない昆虫', 'Creature with Mana Cost Equal to {0}': 'マナ・コストが{0}のクリーチャー',
    'Self-Suspending Instant or Sorcery': '自身を待機するインスタントかソーサリー', 'Legendary Creature': '伝説のクリーチャー', 'Licids': 'リシド', 'Mutant Creature': 'ミュータント・クリーチャー',
    'Green Persist Creature': '頑強を持つ緑のクリーチャー', 'Permanent with "You don\'t lose the game due to having 0 or less life"': '「ライフが0以下でもゲームに敗北しない」パーマネント',
    'Creature with Affinity': '親和を持つクリーチャー', 'Card with "The Ring tempts you"': '「指輪があなたを誘惑する」カード', 'Instant or Sorcery that Targets a Creature and Creates Treasure': 'クリーチャーを対象とし宝物を生成するインスタントかソーサリー',
    'Creature that Returns an Instant or Sorcery from Graveyard to Hand on Entering': '戦場に出たとき墓地のインスタントかソーサリーを手札に戻すクリーチャー',
    'Creature that taps for 2+ mana': 'タップでマナを2点以上出すクリーチャー', 'Artifact / Creature with "{T}: Add Mana" that can tap upon ETB (Mana Rock)': '戦場に出てすぐタップしてマナを出せるアーティファクトかクリーチャー（マナ・アーティファクト）',
    'Goblin Samurai': 'ゴブリン・侍', 'Land that can Animate Itself (Man-Land)': '自身をクリーチャー化できる土地（ミシュラランド）', 'Aura Costing One Mana that Enchants Creatures': 'クリーチャーにつける1マナのオーラ',
    'Eldrazi Creature Card': 'エルドラージ・クリーチャー・カード', 'Spacecraft': '宇宙船', 'Creature That Triggers on Being Tapped': 'タップされたときに誘発するクリーチャー', 'Artifact that is Indestructible': '破壊不能のアーティファクト',
    'Mana Dork or Mana Dork Creator': 'マナ・クリーチャーかそれを生み出すカード', 'Equipment That Gives Haste to a Creature': 'クリーチャーに速攻を与える装備品', 'Card that Makes a Land Creature with a +1/+1 Counter': '土地を+1/+1カウンター付きのクリーチャーにするカード',
    'Legendary Spacecraft': '伝説の宇宙船', 'Man-Land that Enters Untapped': 'アンタップ状態で戦場に出るミシュラランド', 'Creature with Haste': '速攻を持つクリーチャー', 'Dragon Creature': 'ドラゴン・クリーチャー',
    'Creature with MV=0 and toughness=0': 'マナ総量0でタフネス0のクリーチャー', 'Legendary Artifact Creature with no colored cost': '色マナを含まない伝説のアーティファクト・クリーチャー', 'Creature that enters with at least five +1/+1 counters': '+1/+1カウンターを5個以上置かれて戦場に出るクリーチャー',
    'Creature that gains at least 4 life': '4点以上のライフを得るクリーチャー', 'Spacecraft or Planet': '宇宙船か惑星', 'Permanent tapping to deal damage to any target': 'タップして1つを対象にダメージを与えるパーマネント',
    'Instant or Sorcery that deals damage or causes lifeloss to each opponent': '各対戦相手にダメージを与えるかライフを失わせるインスタントかソーサリー', 'Permanent with Affinity and a Generic Mana Cost': '親和と不特定マナ・コストを持つパーマネント',
    'Nonartifact, Nonlegendary Creature with a Generic Mana Cost': '不特定マナ・コストを持つアーティファクトでも伝説でもないクリーチャー', 'Card that Gives a Creature Deathtouch': 'クリーチャーに接死を与えるカード',
    'Spell with Buyback (Mana Payments Only)': 'バイバックを持つ呪文（マナで支払うもの）', 'Merfolk Creature': 'マーフォーク・クリーチャー', 'Creature with dredge': '発掘を持つクリーチャー', 'Legendary Elemental Creature': '伝説のエレメンタル・クリーチャー',
    'Creature Castable with Two or Less Mana': '2マナ以下で唱えられるクリーチャー', 'Any Saga': '英雄譚', 'Desert': '砂漠', 'One mana prepared spell': '1マナの準備された呪文', 'Card with Crew, Saddle and/or Station': '搭乗・騎乗・停留を持つカード',
    'Artifact Creature with Haste': '速攻を持つアーティファクト・クリーチャー', 'Ally Creature': '同盟者クリーチャー', 'Gate That Enters Untapped': 'アンタップ状態で戦場に出る門', 'Artifact Creature That Enters With +1/+1 Counter(s)': '+1/+1カウンターが置かれて戦場に出るアーティファクト・クリーチャー',
    'Creature with "When this creature ETBs, create 1+ creature token(s)"': '戦場に出たときクリーチャー・トークンを生成するクリーチャー', 'Creature with "When this creature ETBs, create 2+ creature tokens"': '戦場に出たときクリーチャー・トークンを2体以上生成するクリーチャー',
    'Saga with Read Ahead': '先読を持つ英雄譚', 'Creature with Morph or Megamorph': '変異か大変異を持つクリーチャー', 'Room Enchantment': '部屋・エンチャント', 'Land that can Animate Itself and Enters Untapped': '自身をクリーチャー化でき、アンタップ状態で戦場に出る土地',
    'Legendary Creature with Haste': '速攻を持つ伝説のクリーチャー', 'Extra Turn Spell': '追加ターン呪文', 'Instant or Sorcery that creates one or more Creature Tokens': 'クリーチャー・トークンを生成するインスタントかソーサリー',
    'Instant or Sorcery that untaps a Creature': 'クリーチャーをアンタップするインスタントかソーサリー', 'Merfolk Creature With Free Tap Ability': 'コストなしのタップ能力を持つマーフォーク・クリーチャー',
    'Card Preventing Combat Damage Dealt To/By a Creature': 'クリーチャーへの／による戦闘ダメージを軽減するカード', 'Card that Creates One or More Creature Tokens Per Turn': '毎ターン、クリーチャー・トークンを生成するカード',
    'Instant That Deals Damage or Causes Lifeloss to Each Opponent': '各対戦相手にダメージを与えるかライフを失わせるインスタント', 'Mana Dork That Adds at Least {G}': '少なくとも{G}を出すマナ・クリーチャー',
    'Mana Dork that Adds At Least {1}{G}': '少なくとも{1}{G}を出すマナ・クリーチャー', 'Activated or triggered abillity that untaps at least five lands': '土地を5つ以上アンタップする能力',
    'Creature that enters with at least two more +1/+1 counters than the amount spent to cast it': '唱えるのに使ったマナより2個以上多い+1/+1カウンターが置かれて戦場に出るクリーチャー',
    'Creature with "Pay Mana: Transform this creature"': '「マナを支払う：変身する」を持つクリーチャー', 'Spike Cycle - {2}, remove a +1/+1 counter: Put a +1/+1 counter': 'スパイク（{2}, +1/+1カウンターを1個取り除く：+1/+1カウンターを1個置く）',
    'Creature with "Sacrifice a Goblin:"': '「ゴブリンを1体生け贄に捧げる：」を持つクリーチャー', 'Creature with "Sacrifice a Saproling:"': '「苗木を1体生け贄に捧げる：」を持つクリーチャー',
    'Creature with Mana Cost Equal to {X}': 'マナ・コストが{X}のクリーチャー', 'Creature with Mana Cost Equal to {X} or {X}{X}': 'マナ・コストが{X}か{X}{X}のクリーチャー', 'Artifact Creature with Mana Cost Equal to {0}': 'マナ・コストが{0}のアーティファクト・クリーチャー',
  });
  const KIND_T = { Creature: 'クリーチャー', Artifact: 'アーティファクト', 'Artifact Creature': 'アーティファクト・クリーチャー', 'Noncreature Artifact': 'クリーチャーでないアーティファクト', Permanent: 'パーマネント',
    'Noncreature permanent': 'クリーチャーでないパーマネント', 'Colorless permanent': '無色のパーマネント', 'Legendary Creature': '伝説のクリーチャー', 'Legendary Artifact': '伝説のアーティファクト', Aura: 'オーラ',
    Vampire: '吸血鬼', Insect: '昆虫', Sliver: 'スリヴァー', Equipment: '装備品', Vehicle: '機体', 'Instant or Sorcery': 'インスタントかソーサリー', Land: '土地', Spell: '呪文' };
  function template(s) {
    if (TEMPLATE[s]) return TEMPLATE[s];
    let m;
    if ((m = s.match(/^(.+?) (?:Castable|castable|That Can Be Cast) for (\{.+?\})(?: that survives)?$/)) && KIND_T[m[1]]) return `${m[2]}で唱えられる${/survives/.test(s) ? '戦場に残る' : ''}${KIND_T[m[1]]}`;
    if ((m = s.match(/^(.+?) Castable for (\{.+?\}) or (\{.+?\})$/)) && KIND_T[m[1]]) return `${m[2]}か${m[3]}で唱えられる${KIND_T[m[1]]}`;
    if ((m = s.match(/^(.+?) with MV ?(<=|>=|=) ?(\d+)$/)) && KIND_T[m[1]]) return `マナ総量${m[3]}${{ '<=': '以下', '>=': '以上', '=': '' }[m[2]]}の${KIND_T[m[1]]}`;
    if ((m = s.match(/^(.+?) with Crew (\d+)(?: or less)?$/)) && KIND_T[m[1]]) return `搭乗${m[2]}${/or less/.test(s) ? '以下' : ''}の${KIND_T[m[1]]}`;
    if ((m = s.match(/^(.+?) with Saddle (\d+) or less$/)) && KIND_T[m[1]]) return `騎乗${m[2]}以下の${KIND_T[m[1]]}`;
    if ((m = s.match(/^Equipment with Equip Cost = (.+)$/))) return `装備コストが${m[1].replace(/, | or /g, 'か')}の装備品`;
    if ((m = s.match(/^Aura with (?:MV<=(\d+)|Cost = (\{.+?\}) and "Enchant Creature")$/))) return m[1] ? `マナ総量${m[1]}以下のオーラ` : `コストが${m[2]}の「クリーチャーにつける」オーラ`;
    if ((m = s.match(/^(.+?) with Mana Cost = (\{.+?\})$/)) && KIND_T[m[1]]) return `マナ・コストが${m[2]}の${KIND_T[m[1]]}`;
    if ((m = s.match(/^Instant or Sorcery that costs (\{.+?\}) or less$/))) return `${m[1]}以下で唱えられるインスタントかソーサリー`;
    if ((m = s.match(/^Legendary (Artifact|Creature) (?:Castable for|with Cost) (.+)$/))) return `${m[2].replace(/ or /g, 'か').replace(/One Mana of Any Color/, '好きな色のマナ1点')}で唱えられる伝説の${KIND_T[m[1]]}`;
    if ((m = s.match(/^Land with (?:"Cycling (\{.+?\})"|Cycling Cost that can be paid using (\{.+?\}))$/))) return `サイクリング・コストが${m[1] || m[2]}の土地`;
    if ((m = s.match(/^(\d+)x (.+)$/))) { const t = template(m[2]); return t && `${t}×${m[1]}`; }
    return null;
  }

  // ---------------------------------------------------------------- card names → «0», «1» …
  const STOP = new Set(['black', 'white', 'green', 'blue', 'red', 'token', 'tokens', 'creature', 'treasure', 'lightning', 'dark', 'grim', 'elvish', 'goblin',
    'ancient', 'great', 'grand', 'high', 'lord', 'lady', 'king', 'queen', 'master', 'elder', 'young', 'old', 'sword', 'ring', 'scepter', 'the',
    'eternal', 'mystic', 'sacred', 'temple', 'tomb', 'path', 'city', 'village', 'phyrexian', 'arcane', 'infinite', 'dramatic', 'rings']);
  function nameForms(name) {
    const forms = new Set([name]);
    for (const part of name.split(' // ')) {
      forms.add(part);
      if (part.includes(', ')) forms.add(part.split(', ')[0]);
      const first = part.split(' ')[0].replace(/,$/, '');
      if (first.length >= 4 && /^[A-Z]/.test(first) && !STOP.has(first.toLowerCase()) && part.includes(' ')) forms.add(first);
    }
    return [...forms].filter(f => f.length >= 3);
  }
  function placeholders(text, cardNames, templateNames) {
    const subs = [];
    cardNames.forEach((n, i) => nameForms(n).forEach(f => subs.push([f, `«${i}»`])));
    (templateNames || []).forEach((n, i) => subs.push([n, `«T${i}»`]));
    subs.sort((a, b) => b[0].length - a[0].length);
    let out = text;
    for (const [f, ph] of subs) out = out.split(f).join(ph);
    return out;
  }
  // one line of steps / prerequisites → Japanese with placeholders, or null
  function line(text, cardNames = [], templateNames = []) {
    const s = placeholders(String(text || '').trim(), cardNames, templateNames).replace(/(«\d+»)'(?!s)/g, "$1's").replace(/\s{2,}/g, ' ');
    if (!s) return null;
    const out = [];
    for (const piece of s.split(/(?<=\.)\s+(?=[A-Z«])/)) {
      const r = sentence(piece);
      if (!r) return null;
      out.push(r + '。');
    }
    return out.join('');
  }
  return { line, result, template, _sentence: sentence, _np: np, _vp: vp };
})();
if (typeof module !== 'undefined') module.exports = COMBO_JA;
