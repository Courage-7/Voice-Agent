import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { SessionState } from '@/types';

interface NeuralCanvas3DProps {
  state: SessionState;
  audioRMS: number;
}

// State Theme Palettes: Multi-Chromatic Iridescent Gradients (Shader Colors)
interface ShaderTheme {
  colorA: [number, number, number]; // Primary Aurora (RGB 0-1)
  colorB: [number, number, number]; // Secondary Fluid (RGB 0-1)
  colorC: [number, number, number]; // Harmonic Wave (RGB 0-1)
  colorD: [number, number, number]; // Rim Accent (RGB 0-1)
  coreColor: [number, number, number]; // Deep Interior (RGB 0-1)
  speed: number;
  displacement: number;
  intensity: number;
}

const SHADER_THEMES: Record<SessionState, ShaderTheme> = {
  DISCONNECTED: {
    colorA: [0.0, 0.75, 0.95], // Cyan
    colorB: [0.06, 0.72, 0.5],  // Mint
    colorC: [0.45, 0.25, 0.85], // Violet
    colorD: [0.92, 0.28, 0.6],  // Rose
    coreColor: [0.03, 0.06, 0.14],
    speed: 0.65,
    displacement: 0.22,
    intensity: 1.4,
  },
  CONNECTED: {
    colorA: [0.06, 0.85, 0.55], // Neon Emerald
    colorB: [0.0, 0.9, 1.0],    // Vivid Cyan
    colorC: [0.55, 0.25, 0.9],  // Purple
    colorD: [0.95, 0.45, 0.2],  // Amber Gold
    coreColor: [0.02, 0.08, 0.12],
    speed: 1.0,
    displacement: 0.28,
    intensity: 1.8,
  },
  LISTENING: {
    colorA: [0.0, 0.94, 1.0],   // Electric Cyan
    colorB: [0.2, 0.85, 0.55],  // Mint Green
    colorC: [0.65, 0.35, 0.98], // Ultraviolet
    colorD: [0.98, 0.3, 0.65],  // Hot Magenta
    coreColor: [0.04, 0.08, 0.18],
    speed: 1.4,
    displacement: 0.35,
    intensity: 2.2,
  },
  USER_SPEAKING: {
    colorA: [0.1, 0.95, 0.55],  // Bright Emerald
    colorB: [0.0, 0.95, 0.9],   // Aquamarine
    colorC: [0.35, 0.9, 0.4],   // Spring Green
    colorD: [0.85, 0.95, 0.2],  // Neon Lime
    coreColor: [0.03, 0.12, 0.09],
    speed: 2.2,
    displacement: 0.48,
    intensity: 2.6,
  },
  THINKING: {
    colorA: [0.65, 0.25, 0.98], // Cosmic Violet
    colorB: [0.92, 0.2, 0.65],  // Electric Magenta
    colorC: [0.3, 0.4, 0.95],   // Royal Blue
    colorD: [0.0, 0.9, 0.95],   // Cyan flare
    coreColor: [0.12, 0.04, 0.22],
    speed: 3.0,
    displacement: 0.45,
    intensity: 2.5,
  },
  SPEAKING: {
    colorA: [0.0, 0.95, 1.0],   // Cyan
    colorB: [0.1, 0.85, 0.5],   // Emerald
    colorC: [0.7, 0.25, 0.95],  // Purple
    colorD: [0.95, 0.3, 0.65],  // Hot Magenta
    coreColor: [0.04, 0.09, 0.18],
    speed: 2.5,
    displacement: 0.55,
    intensity: 2.9,
  },
  MUTED: {
    colorA: [0.85, 0.55, 0.15], // Amber
    colorB: [0.65, 0.45, 0.1],  // Ochre
    colorC: [0.45, 0.35, 0.2],  // Bronze
    colorD: [0.95, 0.65, 0.25], // Warm Gold
    coreColor: [0.12, 0.08, 0.03],
    speed: 0.5,
    displacement: 0.18,
    intensity: 1.2,
  },
  ERROR: {
    colorA: [0.95, 0.2, 0.2],   // Crimson
    colorB: [0.95, 0.5, 0.1],   // Orange
    colorC: [0.6, 0.1, 0.2],    // Dark Red
    colorD: [0.95, 0.8, 0.2],   // Gold
    coreColor: [0.18, 0.03, 0.03],
    speed: 1.5,
    displacement: 0.3,
    intensity: 2.0,
  },
};

// GLSL Simplex Noise Shader Code
const VERTEX_SHADER = `
vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}

float snoise(vec3 v){
  const vec2 C = vec2(1.0/6.0, 1.0/3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i  = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);
  vec3 x1 = x0 - i1 + 1.0 * C.xxx;
  vec3 x2 = x0 - i2 + 2.0 * C.xxx;
  vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
  i = mod(i, 289.0);
  vec4 p = permute(permute(permute(
            i.z + vec4(0.0, i1.z, i2.z, 1.0))
          + i.y + vec4(0.0, i1.y, i2.y, 1.0))
          + i.x + vec4(0.0, i1.x, i2.x, 1.0));
  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);
  vec4 x = x_ *ns.x + ns.yyyy;
  vec4 y = y_ *ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);
  vec4 s0 = floor(b0)*2.0 + 1.0;
  vec4 s1 = floor(b1)*2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
  p0 *= norm.x;
  p1 *= norm.y;
  p2 *= norm.z;
  p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}

uniform float uTime;
uniform float uAudioRMS;
uniform float uDisplacement;
uniform float uSpeed;

varying vec3 vNormal;
varying vec3 vPosition;
varying float vNoise;
varying vec2 vUv;

void main() {
  vUv = uv;
  float t = uTime * uSpeed;
  
  // Dual-frequency harmonic fluid waves
  float n1 = snoise(position * 0.85 + vec3(0.0, t * 0.45, 0.0));
  float n2 = snoise(position * 2.0 - vec3(t * 0.4, t * 0.25, t * 0.15));
  float noise = n1 * 0.65 + n2 * 0.35;
  vNoise = noise;
  
  // Dynamic displacement responding to microphone RMS & speech
  float audioAmp = uDisplacement * (0.15 + uAudioRMS * 1.6);
  float breathing = sin(t * 1.8) * 0.04;
  vec3 displaced = position + normal * (noise * audioAmp + breathing);
  
  vNormal = normalize(normalMatrix * normal);
  vec4 mvPos = modelViewMatrix * vec4(displaced, 1.0);
  vPosition = mvPos.xyz;
  gl_Position = projectionMatrix * mvPos;
}
`;

const FRAGMENT_SHADER = `
uniform vec3 uColorA;
uniform vec3 uColorB;
uniform vec3 uColorC;
uniform vec3 uColorD;
uniform vec3 uCoreColor;
uniform float uAudioRMS;
uniform float uTime;
uniform float uIntensity;

varying vec3 vNormal;
varying vec3 vPosition;
varying float vNoise;
varying vec2 vUv;

void main() {
  vec3 viewDir = normalize(-vPosition);
  vec3 normal = normalize(vNormal);
  
  // Optical Fresnel Rim Glow (Iridescent Bubble Effect)
  float fresnel = 1.0 - max(dot(viewDir, normal), 0.0);
  float rim = pow(fresnel, 2.6);
  float innerGlow = pow(fresnel, 1.3);
  
  // Iridescent Multi-Color Harmonics
  float swirl = sin(vNoise * 4.2 + uTime * 1.6) * 0.5 + 0.5;
  float height = clamp(normal.y * 0.5 + 0.5, 0.0, 1.0);
  
  vec3 band1 = mix(uColorA, uColorB, swirl);
  vec3 band2 = mix(uColorC, uColorD, 1.0 - swirl);
  vec3 surfaceColor = mix(band1, band2, height);
  
  // Deep interior core absorption
  vec3 finalColor = mix(uCoreColor, surfaceColor, innerGlow * 0.85 + 0.15);
  
  // Luminous chromatic rim lighting
  vec3 rimGlowColor = mix(uColorA, uColorD, rim);
  finalColor += rimGlowColor * rim * (2.6 + uAudioRMS * 3.5);
  
  // Specular Highlights (Liquid Sheen)
  vec3 lightDir = normalize(vec3(0.5, 1.2, 0.8));
  vec3 halfVector = normalize(lightDir + viewDir);
  float spec = pow(max(dot(normal, halfVector), 0.0), 36.0);
  finalColor += vec3(1.0) * spec * 0.7;
  
  // Secondary rim light
  vec3 lightDir2 = normalize(vec3(-0.8, -0.6, -0.5));
  vec3 halfVector2 = normalize(lightDir2 + viewDir);
  float spec2 = pow(max(dot(normal, halfVector2), 0.0), 20.0);
  finalColor += uColorB * spec2 * 0.4;
  
  // Glassy Translucency
  float alpha = clamp(0.82 + rim * 0.18 + uAudioRMS * 0.15, 0.0, 1.0);
  gl_FragColor = vec4(finalColor * uIntensity, alpha);
}
`;

export const NeuralCanvas3D: React.FC<NeuralCanvas3DProps> = ({ state, audioRMS }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stateRef = useRef(state);
  const audioRMSRef = useRef(audioRMS);

  stateRef.current = state;
  audioRMSRef.current = audioRMS;

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const scene = new THREE.Scene();

    // Camera: positioned so 2.3 radius sphere never clips on laptop heights
    const camera = new THREE.PerspectiveCamera(40, canvas.clientWidth / canvas.clientHeight, 0.1, 1000);
    camera.position.set(0, 0, 11);

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.35;

    // 1. Core Internal Light & Ambient
    const ambientLight = new THREE.AmbientLight(0x060b18, 2.0);
    scene.add(ambientLight);

    const coreLight = new THREE.PointLight(0x00f0ff, 4.0, 20);
    coreLight.position.set(0, 0, 0);
    scene.add(coreLight);

    // 2. High-Density Fluid Shader Sphere
    const orbRadius = 2.25;
    const geometry = new THREE.SphereGeometry(orbRadius, 96, 96);

    const initialTheme = SHADER_THEMES[stateRef.current] || SHADER_THEMES.DISCONNECTED;

    const shaderMaterial = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      uniforms: {
        uTime: { value: 0.0 },
        uAudioRMS: { value: 0.0 },
        uSpeed: { value: initialTheme.speed },
        uDisplacement: { value: initialTheme.displacement },
        uIntensity: { value: initialTheme.intensity },
        uColorA: { value: new THREE.Vector3(...initialTheme.colorA) },
        uColorB: { value: new THREE.Vector3(...initialTheme.colorB) },
        uColorC: { value: new THREE.Vector3(...initialTheme.colorC) },
        uColorD: { value: new THREE.Vector3(...initialTheme.colorD) },
        uCoreColor: { value: new THREE.Vector3(...initialTheme.coreColor) },
      },
      transparent: true,
      depthWrite: false,
    });

    const orbMesh = new THREE.Mesh(geometry, shaderMaterial);
    scene.add(orbMesh);

    // 3. Inner Glowing Star Core
    const innerGeo = new THREE.SphereGeometry(0.85, 32, 32);
    const innerMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.85,
    });
    const innerCore = new THREE.Mesh(innerGeo, innerMat);
    scene.add(innerCore);

    // 4. Gyroscopic Orbital Rings with Stardust Halos
    const createGyroRing = (radius: number, particleCount: number, colorHex: number, tiltX: number, tiltZ: number) => {
      const ringGeo = new THREE.BufferGeometry();
      const pos = new Float32Array(particleCount * 3);
      for (let i = 0; i < particleCount; i++) {
        const angle = (i / particleCount) * Math.PI * 2;
        const spread = (Math.sin(i * 3.7) * 0.5) * 0.15;
        pos[i * 3] = Math.cos(angle) * (radius + spread);
        pos[i * 3 + 1] = spread * 1.2;
        pos[i * 3 + 2] = Math.sin(angle) * (radius + spread);
      }
      ringGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      const ringMat = new THREE.PointsMaterial({
        color: colorHex,
        size: 0.065,
        transparent: true,
        opacity: 0.75,
        blending: THREE.AdditiveBlending,
      });
      const points = new THREE.Points(ringGeo, ringMat);
      points.rotation.x = tiltX;
      points.rotation.z = tiltZ;
      return points;
    };

    const ring1 = createGyroRing(3.2, 180, 0x00f0ff, Math.PI / 3, Math.PI / 8);
    scene.add(ring1);

    const ring2 = createGyroRing(3.6, 150, 0x10b981, -Math.PI / 3.5, -Math.PI / 6);
    scene.add(ring2);

    const ring3 = createGyroRing(4.0, 120, 0xa855f7, Math.PI / 6, -Math.PI / 4);
    scene.add(ring3);

    // 5. Floating Weightless Stardust Embers
    const stardustCount = 140;
    const stardustGeo = new THREE.BufferGeometry();
    const stardustPos = new Float32Array(stardustCount * 3);
    for (let i = 0; i < stardustCount * 3; i += 3) {
      stardustPos[i] = (Math.sin(i * 2.1) * 0.5) * 16;
      stardustPos[i + 1] = (Math.cos(i * 1.7) * 0.5) * 12;
      stardustPos[i + 2] = (Math.sin(i * 3.3) * 0.5) * 10;
    }
    stardustGeo.setAttribute('position', new THREE.BufferAttribute(stardustPos, 3));
    const stardustMat = new THREE.PointsMaterial({
      color: 0x38bdf8,
      size: 0.05,
      transparent: true,
      opacity: 0.45,
      blending: THREE.AdditiveBlending,
    });
    const stardust = new THREE.Points(stardustGeo, stardustMat);
    scene.add(stardust);

    // Mouse Parallax
    let targetCamX = 0;
    let targetCamY = 0;

    const onMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      const y = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
      targetCamX = x * 0.8;
      targetCamY = -y * 0.6;
    };

    const onResize = () => {
      if (!canvas) return;
      camera.aspect = canvas.clientWidth / canvas.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('resize', onResize);

    const clock = new THREE.Clock();
    let reqId: number;

    // Smooth lerping color vectors
    const curColorA = new THREE.Vector3(...initialTheme.colorA);
    const curColorB = new THREE.Vector3(...initialTheme.colorB);
    const curColorC = new THREE.Vector3(...initialTheme.colorC);
    const curColorD = new THREE.Vector3(...initialTheme.colorD);
    const curCore = new THREE.Vector3(...initialTheme.coreColor);

    const animate = () => {
      reqId = requestAnimationFrame(animate);
      const time = clock.getElapsedTime();
      const theme = SHADER_THEMES[stateRef.current] || SHADER_THEMES.DISCONNECTED;
      const rms = audioRMSRef.current;

      // Color lerp
      curColorA.lerp(new THREE.Vector3(...theme.colorA), 0.08);
      curColorB.lerp(new THREE.Vector3(...theme.colorB), 0.08);
      curColorC.lerp(new THREE.Vector3(...theme.colorC), 0.08);
      curColorD.lerp(new THREE.Vector3(...theme.colorD), 0.08);
      curCore.lerp(new THREE.Vector3(...theme.coreColor), 0.08);

      shaderMaterial.uniforms.uTime.value = time;
      shaderMaterial.uniforms.uAudioRMS.value = rms;
      shaderMaterial.uniforms.uSpeed.value = theme.speed;
      shaderMaterial.uniforms.uDisplacement.value = theme.displacement;
      shaderMaterial.uniforms.uIntensity.value = theme.intensity;
      shaderMaterial.uniforms.uColorA.value.copy(curColorA);
      shaderMaterial.uniforms.uColorB.value.copy(curColorB);
      shaderMaterial.uniforms.uColorC.value.copy(curColorC);
      shaderMaterial.uniforms.uColorD.value.copy(curColorD);
      shaderMaterial.uniforms.uCoreColor.value.copy(curCore);

      // Camera parallax
      camera.position.x += (targetCamX - camera.position.x) * 0.04;
      camera.position.y += (targetCamY - camera.position.y) * 0.04;
      camera.lookAt(0, 0, 0);

      // Inner Core Pulse
      const coreScale = 1.0 + Math.sin(time * 2.5) * 0.08 + rms * 0.4;
      innerCore.scale.set(coreScale, coreScale, coreScale);
      coreLight.intensity = 3.5 + Math.sin(time * 2.0) * 0.5 + rms * 4.0;

      // Smooth 3D Rotations
      orbMesh.rotation.y += 0.004 * theme.speed;
      orbMesh.rotation.x += 0.002 * theme.speed;
      ring1.rotation.y += 0.006 * theme.speed;
      ring2.rotation.y -= 0.005 * theme.speed;
      ring3.rotation.x += 0.004 * theme.speed;
      stardust.rotation.y += 0.0003;

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(reqId);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize', onResize);
      renderer.dispose();
      geometry.dispose();
      shaderMaterial.dispose();
      innerGeo.dispose();
      innerMat.dispose();
      ring1.geometry.dispose();
      (ring1.material as THREE.Material).dispose();
      ring2.geometry.dispose();
      (ring2.material as THREE.Material).dispose();
      ring3.geometry.dispose();
      (ring3.material as THREE.Material).dispose();
      stardustGeo.dispose();
      stardustMat.dispose();
    };
  }, []);

  return (
    <div className="relative w-full h-full flex items-center justify-center overflow-hidden">
      {/* Dynamic Multi-layered Aurora Ambient Bloom */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-80 h-80 rounded-full bg-gradient-to-tr from-[#00F0FF]/15 via-[#10B981]/15 to-[#8B5CF6]/15 blur-[90px] animate-pulse" />
      </div>
      <canvas
        ref={canvasRef}
        className="w-full h-full block cursor-default relative z-10"
      />
    </div>
  );
};
