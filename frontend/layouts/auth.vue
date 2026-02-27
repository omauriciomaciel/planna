<script setup lang="ts">
const chartCanvas = ref<HTMLCanvasElement | null>(null)
let animationId: number | null = null

onMounted(() => {
  const canvas = chartCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // Game Boy DMG palette — 4 shades only
  const GB = {
    bg:     '#0f380f',
    dark:   '#306230',
    light:  '#8bac0f',
    bright: '#9bbc0f',
  }

  // Canvas is 48×32 internal, displayed at 192×128 (4× scale)
  const LW = 48
  const LH = 32
  const FLOOR = LH - 4

  // Fill a pixel-perfect ellipse in logical coords
  function fillEllipse(cx: number, cy: number, rw: number, rh: number, color: string) {
    if (rw <= 0 || rh <= 0) return
    ctx.fillStyle = color
    for (let dy = -rh; dy <= rh; dy++) {
      for (let dx = -rw; dx <= rw; dx++) {
        if ((dx / rw) ** 2 + (dy / rh) ** 2 <= 1) {
          ctx.fillRect(Math.round(cx + dx), Math.round(cy + dy), 1, 1)
        }
      }
    }
  }

  interface Coin {
    x: number; y: number
    vx: number; vy: number
    spinPhase: number; spinSpeed: number
    r: number; bounces: number
  }

  interface Sparkle {
    x: number; y: number; life: number
  }

  function newCoin(stagger = 0): Coin {
    return {
      x: 5 + Math.random() * (LW - 10),
      y: -6 - stagger,
      vx: (Math.random() - 0.5) * 0.3,
      vy: 0.6 + Math.random() * 0.8,
      spinPhase: Math.random() * Math.PI * 2,
      spinSpeed: 0.055 + Math.random() * 0.045,
      r: 4,
      bounces: 0,
    }
  }

  // 4 coins staggered so they don't all arrive together
  const coins: Coin[] = Array.from({ length: 4 }, (_, i) => newCoin(i * 9))
  const sparkles: Sparkle[] = []

  function drawCoin(coin: Coin) {
    const rh = coin.r
    const rw = Math.max(0, Math.round(Math.abs(Math.cos(coin.spinPhase)) * coin.r))
    if (rw === 0) return

    const cx = Math.round(coin.x)
    const cy = Math.round(coin.y)

    // Dark outline
    fillEllipse(cx, cy, rw + 1, rh + 1, GB.dark)
    // Coin body
    fillEllipse(cx, cy, rw, rh, GB.light)
    // Highlight — top-left quadrant
    if (rw >= 2) {
      fillEllipse(
        cx - Math.max(1, Math.round(rw * 0.3)),
        cy - Math.max(1, Math.round(rh * 0.2)),
        Math.max(1, Math.round(rw * 0.42)),
        Math.max(1, Math.round(rh * 0.36)),
        GB.bright,
      )
    }
  }

  function update() {
    const GRAVITY = 0.09
    coins.forEach((coin) => {
      coin.vy += GRAVITY
      coin.y += coin.vy
      coin.x += coin.vx
      coin.spinPhase += coin.spinSpeed

      // Wrap horizontally
      if (coin.x < -coin.r) coin.x = LW + coin.r
      if (coin.x > LW + coin.r) coin.x = -coin.r

      // Bounce off floor
      if (coin.y + coin.r >= FLOOR) {
        coin.y = FLOOR - coin.r
        coin.vy *= -0.52
        coin.bounces++
        // Sparkle on impact
        sparkles.push({ x: Math.round(coin.x), y: FLOOR - 1, life: 6 })
        // Respawn after settling
        if (Math.abs(coin.vy) < 0.12 || coin.bounces >= 5) {
          Object.assign(coin, newCoin())
        }
      }
    })
    sparkles.forEach(s => s.life--)
    sparkles.splice(0, sparkles.length, ...sparkles.filter(s => s.life > 0))
  }

  function draw() {
    // GB screen background
    ctx.fillStyle = GB.bg
    ctx.fillRect(0, 0, LW, LH)

    // Subtle dot texture
    ctx.fillStyle = GB.dark
    for (let y = 2; y < FLOOR - 1; y += 4) {
      for (let x = 2; x < LW; x += 4) {
        ctx.fillRect(x, y, 1, 1)
      }
    }

    // Floor: two-tone line
    ctx.fillStyle = GB.dark
    ctx.fillRect(0, FLOOR, LW, 1)
    ctx.fillStyle = GB.light
    ctx.fillRect(0, FLOOR + 1, LW, 1)
    ctx.fillStyle = GB.dark
    ctx.fillRect(0, FLOOR + 2, LW, LH - FLOOR - 2)

    // Coins
    coins.forEach(drawCoin)

    // Impact sparkles — 4 diagonal pixels
    sparkles.forEach((s) => {
      ctx.fillStyle = GB.bright
      ctx.fillRect(s.x - 1, s.y - 1, 1, 1)
      ctx.fillRect(s.x + 1, s.y - 1, 1, 1)
      ctx.fillRect(s.x - 1, s.y + 1, 1, 1)
      ctx.fillRect(s.x + 1, s.y + 1, 1, 1)
    })
  }

  function loop() {
    update()
    draw()
    animationId = requestAnimationFrame(loop)
  }

  loop()
})

onUnmounted(() => {
  if (animationId !== null) cancelAnimationFrame(animationId)
})
</script>

<template>
  <div class="min-h-screen bg-gray-950 lg:grid lg:grid-cols-2">
    <!-- Brand panel — desktop only -->
    <div
      class="hidden lg:flex flex-col justify-between p-14 relative overflow-hidden border-r border-white/5"
      style="background-color: #0e1411"
    >
      <!-- Ledger dot grid -->
      <div
        class="absolute inset-0 pointer-events-none"
        style="background-image: radial-gradient(circle, rgba(52, 211, 153, 0.18) 1px, transparent 1px); background-size: 28px 28px; opacity: 0.4"
      />

      <!-- Logo -->
      <div class="relative flex items-center gap-3">
        <div
          class="w-8 h-8 rounded-lg flex items-center justify-center"
          style="background: rgba(52, 211, 153, 0.1); border: 1px solid rgba(52, 211, 153, 0.2)"
        >
          <span class="text-emerald-400 font-bold text-sm leading-none">P</span>
        </div>
        <span class="text-white/80 font-semibold text-base tracking-tight">Planna</span>
      </div>

      <!-- 8-bit coin animation -->
      <div class="relative flex justify-center">
        <!-- Game Boy screen bezel -->
        <div style="background: #0a0a0a; border-radius: 3px; padding: 10px 12px 8px; border: 1px solid rgba(255,255,255,0.06)">
          <!-- Screen inner shadow -->
          <div
            class="relative"
            style="box-shadow: inset 0 0 16px rgba(0,0,0,0.8)"
          >
            <!-- CRT scanlines -->
            <div
              class="absolute inset-0 pointer-events-none z-10"
              style="background: repeating-linear-gradient(0deg, transparent, transparent 1px, rgba(0,0,0,0.12) 1px, rgba(0,0,0,0.12) 2px)"
            />
            <canvas
              ref="chartCanvas"
              width="48"
              height="32"
              style="display: block; width: 192px; height: 128px; image-rendering: pixelated; image-rendering: crisp-edges"
            />
          </div>
          <!-- Label -->
          <div
            class="mt-2 text-center"
            style="font-family: monospace; font-size: 9px; letter-spacing: 0.18em; color: rgba(52,211,153,0.3)"
          >
            PLANNA OS v1.0
          </div>
        </div>
      </div>

      <!-- Tagline -->
      <div class="relative">
        <p class="text-white/70 text-xl font-medium leading-snug max-w-xs">
          Clareza sobre o seu dinheiro,<br>mês a mês.
        </p>
        <p class="text-white/25 text-sm mt-4">Gestão financeira pessoal</p>
      </div>
    </div>

    <!-- Form panel -->
    <div class="flex items-center justify-center p-8 min-h-screen lg:min-h-0">
      <div class="w-full max-w-[360px]">
        <!-- Mobile logo -->
        <div class="flex items-center gap-2.5 mb-10 lg:hidden">
          <div
            class="w-7 h-7 rounded-lg flex items-center justify-center"
            style="background: rgba(52, 211, 153, 0.1); border: 1px solid rgba(52, 211, 153, 0.2)"
          >
            <span class="text-emerald-400 font-bold text-xs leading-none">P</span>
          </div>
          <span class="text-white/80 font-semibold text-base tracking-tight">Planna</span>
        </div>

        <slot />
      </div>
    </div>
  </div>
</template>
