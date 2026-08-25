import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { SessionState } from '@/types';

interface NeuralCanvas3DProps {
  state: SessionState;
  audioRMS: number;
}

const STATE_PALETTES: Record<SessionState, { color: number; emissive: number; roughness: number; metalness: number; speed: number }> = {
  DISCONNECTED: { color: 0x18181c, emissive: 0x09090b, roughness: 0.35, metalness: 0.6, speed: 0.4 },
  CONNECTED: { color: 0x0d2818, emissive: 0x052e16, roughness: 0.15, metalness: 0.85, speed: 0.8 },
  LISTENING: { color: 0x064e3b, emissive: 0x022c22, roughness: 0.1, metalness: 0.9, speed: 1.2 },
  USER_SPEAKING: { color: 0x065f46, emissive: 0x047857, roughness: 0.08, metalness: 0.95, speed: 2.2 },
  THINKING: { color: 0x78350f, emissive: 0x451a03, roughness: 0.12, metalness: 0.85, speed: 3.0 },
  SPEAKING: { color: 0x047857, emissive: 0x065f46, roughness: 0.08, metalness: 0.92, speed: 2.0 },
  ERROR: { color: 0x7f1d1d, emissive: 0x450a0a, roughness: 0.2, metalness: 0.7, speed: 1.5 },
};

// Simplex-style 3D noise function for procedural organic liquid deformation
function createNoise() {
  const p = new Uint8Array(512);
  for (let i = 0; i < 256; i++) p[i] = p[256 + i] = Math.floor(Math.random() * 256);

  function fade(t: number) { return t * t * t * (t * (t * 6 - 15) + 10); }
  function lerp(t: number, a: number, b: number) { return a + t * (b - a); }
  function grad(hash: number, x: number, y: number, z: number) {
    const h = hash & 15;
    const u = h < 8 ? x : y;
    const v = h < 4 ? y : h === 12 || h === 14 ? x : z;
    return ((h & 1) === 0 ? u : -u) + ((h & 2) === 0 ? v : -v);
  }

  return function (x: number, y: number, z: number) {
    const X = Math.floor(x) & 255;
    const Y = Math.floor(y) & 255;
    const Z = Math.floor(z) & 255;

    x -= Math.floor(x);
    y -= Math.floor(y);
    z -= Math.floor(z);

    const u = fade(x);
    const v = fade(y);
    const w = fade(z);

    const A = p[X] + Y;
    const AA = p[A] + Z;
    const AB = p[A + 1] + Z;
    const B = p[X + 1] + Y;
    const BA = p[B] + Z;
    const BB = p[B + 1] + Z;

    return lerp(
      w,
      lerp(
        v,
        lerp(u, grad(p[AA], x, y, z), grad(p[BA], x - 1, y, z)),
        lerp(u, grad(p[AB], x, y - 1, z), grad(p[BB], x - 1, y - 1, z))
      ),
      lerp(
        v,
        lerp(u, grad(p[AA + 1], x, y, z - 1), grad(p[BA + 1], x - 1, y, z - 1)),
        lerp(u, grad(p[AB + 1], x, y - 1, z - 1), grad(p[BB + 1], x - 1, y - 1, z - 1))
      )
    );
  };
}

const noise3D = createNoise();

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
    scene.fog = new THREE.FogExp2(0x09090b, 0.035);

    const camera = new THREE.PerspectiveCamera(40, canvas.clientWidth / canvas.clientHeight, 0.1, 1000);
    camera.position.set(0, 0, 18);

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;

    // Organic Ambient & Key Lighting
    const ambientLight = new THREE.AmbientLight(0x09090b, 2.5);
    scene.add(ambientLight);

    const emeraldLight = new THREE.DirectionalLight(0x10b981, 2.5);
    emeraldLight.position.set(8, 12, 10);
    scene.add(emeraldLight);

    const backRimLight = new THREE.DirectionalLight(0x34d399, 1.8);
    backRimLight.position.set(-8, -10, -8);
    scene.add(backRimLight);

    const softFillLight = new THREE.PointLight(0xffffff, 1.2, 30);
    softFillLight.position.set(0, 5, 8);
    scene.add(softFillLight);

    // High-subdivision Fluid Sphere
    const baseRadius = 4.2;
    const geometry = new THREE.IcosahedronGeometry(baseRadius, 32);
    const originalPositions = geometry.attributes.position.array.slice() as Float32Array;

    const material = new THREE.MeshPhysicalMaterial({
      color: 0x064e3b,
      emissive: 0x022c22,
      roughness: 0.12,
      metalness: 0.9,
      clearcoat: 0.8,
      clearcoatRoughness: 0.15,
      reflectivity: 0.9,
      wireframe: false,
    });

    const liquidOrb = new THREE.Mesh(geometry, material);
    scene.add(liquidOrb);

    // Ambient floating dust particles (clean, sparse, subtle)
    const particleCount = 180;
    const particleGeo = new THREE.BufferGeometry();
    const particlePos = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePos[i] = (Math.random() - 0.5) * 26;
      particlePos[i + 1] = (Math.random() - 0.5) * 20;
      particlePos[i + 2] = (Math.random() - 0.5) * 16;
    }
    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePos, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0x10b981,
      size: 0.08,
      transparent: true,
      opacity: 0.4,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // Mouse Parallax
    let targetCameraX = 0;
    let targetCameraY = 0;

    const onMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      const y = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
      targetCameraX = x * 1.8;
      targetCameraY = -y * 1.4;
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
    let currentColor = new THREE.Color(0x064e3b);
    let reqId: number;

    const animate = () => {
      reqId = requestAnimationFrame(animate);
      const time = clock.getElapsedTime();
      const palette = STATE_PALETTES[stateRef.current] || STATE_PALETTES.DISCONNECTED;
      const targetCol = new THREE.Color(palette.color);
      const targetEmissive = new THREE.Color(palette.emissive);

      currentColor.lerp(targetCol, 0.05);
      material.color.copy(currentColor);
      material.emissive.lerp(targetEmissive, 0.05);
      material.roughness = THREE.MathUtils.lerp(material.roughness, palette.roughness, 0.05);
      material.metalness = THREE.MathUtils.lerp(material.metalness, palette.metalness, 0.05);

      // Smooth camera interpolation
      camera.position.x += (targetCameraX - camera.position.x) * 0.05;
      camera.position.y += (targetCameraY - camera.position.y) * 0.05;
      camera.lookAt(0, 0, 0);

      // Organic fluid vertex displacement based on noise and audio RMS
      const positionAttr = geometry.attributes.position;
      const currentRMS = audioRMSRef.current;
      const noiseFrequency = 0.55;
      const speed = palette.speed * 0.8;
      const displacementAmount = 0.35 + currentRMS * 1.6;

      for (let i = 0; i < positionAttr.count; i++) {
        const ox = originalPositions[i * 3];
        const oy = originalPositions[i * 3 + 1];
        const oz = originalPositions[i * 3 + 2];

        const noiseVal = noise3D(
          ox * noiseFrequency + time * speed * 0.3,
          oy * noiseFrequency + time * speed * 0.3,
          oz * noiseFrequency + time * speed * 0.3
        );

        const factor = 1.0 + (noiseVal * displacementAmount * 0.3) + (currentRMS * 0.08);

        positionAttr.setXYZ(i, ox * factor, oy * factor, oz * factor);
      }

      positionAttr.needsUpdate = true;
      geometry.computeVertexNormals();

      liquidOrb.rotation.y += 0.003 * palette.speed;
      liquidOrb.rotation.x += 0.0015 * palette.speed;
      particles.rotation.y += 0.0004;

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(reqId);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize', onResize);
      renderer.dispose();
      geometry.dispose();
      material.dispose();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full block cursor-default"
    />
  );
};
