const JUSTICE_DEFAULT = {
  Judgement: 5,
  Urbanism: 5,
  Strength: 5,
  Tactics: 5,
  Intimidation: 5,
  Cunning: 5,
  Endurance: 5,
};

const QUESTS = [
  {
    id: 'tea',
    title: 'Tea Crimes Unit',
    summary: 'A ration ring is selling illicit premium tea from a shuttered kiosk beneath the civic plaza.',
  },
  {
    id: 'pigeons',
    title: 'Unlicensed Pigeons',
    summary: 'A resident insists the pigeons near Nelson Column are gathering state secrets.',
  },
  {
    id: 'bins',
    title: 'Bin Chute Rebellion',
    summary: 'Tenants in Hab-Block Albion have declared independence over waste-disposal rights.',
  },
];

const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');

const state = {
  justice: { ...JUSTICE_DEFAULT },
  quest: QUESTS[0],
  inventory: [],
  log: [
    'Booted into Trafalgar Grid. Smells like rain, concrete, and public resentment.',
    'Case priority: investigate quota manipulation at the civic plaza.',
    'Secondary lead: tea contraband moving under the east skybridge.',
  ],
  player: { x: 0, y: 40, r: 12, speed: 180 },
  keys: {},
  pickups: [
    { id: 1, x: 120, y: 90, kind: 'Evidence' },
    { id: 2, x: -130, y: -60, kind: 'Med Kit' },
    { id: 3, x: 200, y: -190, kind: 'Case File' },
  ],
  enemies: [
    { baseX: 140, baseY: 140, x: 140, y: 140, color: '#ef4444' },
    { baseX: -130, baseY: 120, x: -130, y: 120, color: '#a855f7' },
    { baseX: 70, baseY: -140, x: 70, y: -140, color: '#ef4444' },
    { baseX: -190, baseY: -160, x: -190, y: -160, color: '#a855f7' },
  ],
};

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener('resize', resize);
resize();

window.addEventListener('keydown', (e) => (state.keys[e.key.toLowerCase()] = true));
window.addEventListener('keyup', (e) => (state.keys[e.key.toLowerCase()] = false));

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function pushLog(message) {
  state.log = [message, ...state.log].slice(0, 6);
  syncHud();
}

function handleCollect(kind) {
  if (!state.inventory.includes(kind)) {
    state.inventory.push(kind);
  }
  pushLog(`Collected ${kind}. Paperwork intensifies.`);
  if (kind === 'Evidence' || kind === 'Case File') {
    state.justice.Judgement += 1;
    state.justice.Cunning += 1;
    state.quest = QUESTS[1];
  }
  if (kind === 'Med Kit') {
    state.justice.Endurance += 1;
  }
  syncHud();
}

function syncHud() {
  document.getElementById('quest-title').textContent = state.quest.title;
  document.getElementById('quest-summary').textContent = state.quest.summary;

  const stats = document.getElementById('stats');
  stats.innerHTML = Object.entries(state.justice)
    .map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`)
    .join('');

  document.getElementById('log').innerHTML = state.log.map((x) => `<div>${x}</div>`).join('');

  const inventory = document.getElementById('inventory');
  inventory.innerHTML = state.inventory.length
    ? state.inventory.map((x) => `<span class="tag">${x}</span>`).join('')
    : '<span class="empty">Empty. Typical bureaucracy.</span>';

  document.getElementById('position').textContent = `Position: ${Math.round(state.player.x)}, ${Math.round(state.player.y)}`;
}

syncHud();

setInterval(() => {
  const choices = [
    'Citizen report: suspicious pigeons circling Nelson-tier monument.',
    'Dispatch: Hab-Block Albion requests armed mediation over bin chute jurisdiction.',
    'Alert: vending kiosk AI has filed three assault claims and one emotional grievance.',
  ];
  pushLog(choices[Math.floor(Math.random() * choices.length)]);
}, 7000);

let last = performance.now();
function loop(now) {
  const delta = Math.min(0.033, (now - last) / 1000);
  last = now;

  const sprint = state.keys.shift ? 1.7 : 1;
  const dx = (state.keys.d ? 1 : 0) - (state.keys.a ? 1 : 0);
  const dy = (state.keys.s ? 1 : 0) - (state.keys.w ? 1 : 0);
  const len = Math.hypot(dx, dy) || 1;

  state.player.x = clamp(state.player.x + ((dx / len) * state.player.speed * sprint * delta), -260, 260);
  state.player.y = clamp(state.player.y + ((dy / len) * state.player.speed * sprint * delta), -260, 260);

  const t = now * 0.001;
  for (const enemy of state.enemies) {
    enemy.x = enemy.baseX + Math.sin(t + enemy.baseX) * 32;
    enemy.y = enemy.baseY + Math.cos(t * 1.3 + enemy.baseY) * 32;
  }

  state.pickups = state.pickups.filter((item) => {
    const dist = Math.hypot(item.x - state.player.x, item.y - state.player.y);
    if (dist < 22) {
      handleCollect(item.kind);
      return false;
    }
    return true;
  });

  render();
  syncHud();
  requestAnimationFrame(loop);
}

function drawWorld() {
  const camX = state.player.x;
  const camY = state.player.y;

  const toScreen = (x, y) => ({
    x: canvas.width / 2 + (x - camX),
    y: canvas.height / 2 + (y - camY),
  });

  ctx.fillStyle = '#0f172a';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  for (let i = -600; i <= 600; i += 30) {
    ctx.strokeStyle = 'rgba(148,163,184,.14)';
    const a = toScreen(i, -600);
    const b = toScreen(i, 600);
    const c = toScreen(-600, i);
    const d = toScreen(600, i);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(c.x, c.y);
    ctx.lineTo(d.x, d.y);
    ctx.stroke();
  }

  const buildings = [
    { x: 0, y: 0, w: 220, h: 220, color: '#374151' },
    { x: 220, y: -180, w: 80, h: 80, color: '#1e293b' },
    { x: -230, y: 190, w: 110, h: 70, color: '#334155' },
    { x: -260, y: -200, w: 90, h: 90, color: '#475569' },
  ];
  for (const b of buildings) {
    const p = toScreen(b.x, b.y);
    ctx.fillStyle = b.color;
    ctx.fillRect(p.x - b.w / 2, p.y - b.h / 2, b.w, b.h);
  }

  for (const item of state.pickups) {
    const p = toScreen(item.x, item.y);
    ctx.fillStyle = item.kind === 'Med Kit' ? '#10b981' : '#60a5fa';
    ctx.beginPath();
    ctx.arc(p.x, p.y, 9, 0, Math.PI * 2);
    ctx.fill();
  }

  for (const enemy of state.enemies) {
    const p = toScreen(enemy.x, enemy.y);
    ctx.fillStyle = enemy.color;
    ctx.fillRect(p.x - 10, p.y - 10, 20, 20);
  }

  const pp = toScreen(state.player.x, state.player.y);
  ctx.fillStyle = '#f59e0b';
  ctx.beginPath();
  ctx.arc(pp.x, pp.y, state.player.r, 0, Math.PI * 2);
  ctx.fill();
}

function render() {
  drawWorld();
}

requestAnimationFrame(loop);
