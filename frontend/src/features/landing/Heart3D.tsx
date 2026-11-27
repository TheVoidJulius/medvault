import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { MarchingCubes } from 'three/examples/jsm/objects/MarchingCubes.js';

/**
 * A procedural "printed organ" heart, rendered in real time.
 *
 * - Muscle: a metaball field (marching cubes) shaped as a broad, rounded ventricle mass with
 *   atria and an apex tipped down and to the right.
 * - Panel seams: drawn in the fragment shader where the surface crosses a few cutting planes,
 *   so the lower body reads as moulded plates.
 * - Great vessels: short, thick pipe stubs with ribbed metal ferrules.
 * - Look: polished chrome lit by a studio of strip lights and a blue panel; scroll turns it into
 *   frosted white plastic with metal seams and a small barcode label.
 * Dragging rotates it; it settles back with inertia.
 */

export interface HeartStage {
  /** 0..1 how far chrome has turned to frosted white */
  white: number;
  /** uniform scale multiplier */
  scale: number;
  /** offset in canvas-relative units (-1..1) */
  x: number;
  y: number;
  /** extra spin from scroll, radians */
  spin: number;
}

const CHROME = { color: new THREE.Color('#e9ecf2'), metalness: 1, roughness: 0.08 };
const WHITE = { color: new THREE.Color('#f2f1ee'), metalness: 0, roughness: 0.7 };

/** Studio for reflections: grey walls, bright and dark vertical strips, one large blue panel. */
function buildStudio(pmrem: THREE.PMREMGenerator) {
  const studio = new THREE.Scene();
  studio.add(new THREE.Mesh(new THREE.BoxGeometry(24, 14, 24), new THREE.MeshBasicMaterial({ color: '#8d9097', side: THREE.BackSide })));
  const panel = (x: number, y: number, z: number, w: number, h: number, color: string, k: number) => {
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(k), side: THREE.DoubleSide }),
    );
    m.position.set(x, y, z);
    m.lookAt(0, y, 0);
    studio.add(m);
  };
  // alternating light and dark strips give chrome its banded reflections
  const ring = 7.5;
  for (let i = 0; i < 14; i++) {
    const a = (i / 14) * Math.PI * 2;
    const light = i % 2 === 0;
    panel(Math.cos(a) * ring, 0, Math.sin(a) * ring, light ? 1.6 : 0.9, 11, light ? '#ffffff' : '#16181c', light ? 2.4 : 1);
  }
  panel(-6.8, 0.5, 1.5, 4, 7, '#4f66ff', 1.1); // blue panel, viewer's left: a cool edge, not a wash
  panel(0, 6.8, 0, 10, 10, '#ffffff', 1.4); // soft top light
  const tex = pmrem.fromScene(studio, 0.015).texture;
  studio.traverse((o) => (o as THREE.Mesh).geometry?.dispose?.());
  return tex;
}

function buildMuscle(material: THREE.Material) {
  const mc = new MarchingCubes(76, material, false, false, 120000);
  mc.isolation = 78;
  mc.reset();
  // [x, y, z, strength] in the 0..1 field; y up, z toward the viewer
  const balls: [number, number, number, number][] = [
    [0.68, 0.13, 0.52, 0.35], // pointed apex, down and to the viewer's right
    [0.64, 0.21, 0.52, 0.75],
    [0.58, 0.31, 0.51, 1.15],
    [0.5, 0.44, 0.5, 1.6], // broad upper ventricles
    [0.37, 0.42, 0.55, 1.05], // right ventricle bulge on the viewer's left
    [0.64, 0.46, 0.47, 0.95], // left ventricle
    [0.5, 0.56, 0.5, 0.75], // narrower base
    [0.37, 0.6, 0.54, 0.45], // right atrium
    [0.63, 0.6, 0.43, 0.4], // left atrium
  ];
  for (const [x, y, z, s] of balls) mc.addBall(x, y, z, s, 12);
  mc.update();
  return mc;
}

/** Inject panel seams into the muscle material. uWhite blends the seam from dark groove to metal inlay. */
function addSeams(material: THREE.MeshPhysicalMaterial, uniforms: { uWhite: { value: number } }) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uWhite = uniforms.uWhite;
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vObj;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvObj = position;');
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        `#include <common>
varying vec3 vObj;
uniform float uWhite;
float seamLine(vec3 p, vec3 n, float o) { return abs(dot(p, normalize(n)) - o); }
float seams(vec3 p) {
  float w = 0.008;
  // a band around the lower third of the ventricles
  float band = seamLine(p, vec3(0.25, 1.0, 0.1), -0.33);
  // a seam running down the front from the band to the apex
  float front = seamLine(p, vec3(1.0, 0.18, -0.25), 0.08);
  front = p.y < -0.33 ? front : 1.0;
  // a diagonal seam between the ventricles and the atria
  float upper = seamLine(p, vec3(-0.55, 1.0, 0.15), 0.02);
  upper = (p.y > -0.33 && p.y < 0.28) ? upper : 1.0;
  float side = seamLine(p, vec3(1.0, -0.35, 0.6), -0.32);
  side = p.y < -0.05 ? side : 1.0;
  float d = min(min(band, front), min(upper, side));
  return 1.0 - smoothstep(w * 0.35, w, d);
}`,
      )
      .replace(
        '#include <color_fragment>',
        `#include <color_fragment>
float sm = seams(vObj);
vec3 seamCol = mix(vec3(0.05, 0.055, 0.07), vec3(0.62, 0.64, 0.68), uWhite);
diffuseColor.rgb = mix(diffuseColor.rgb, seamCol, sm * 0.92);`,
      )
      .replace(
        '#include <roughnessmap_fragment>',
        `#include <roughnessmap_fragment>
roughnessFactor = mix(roughnessFactor, 0.32, sm);`,
      )
      .replace(
        '#include <metalnessmap_fragment>',
        `#include <metalnessmap_fragment>
metalnessFactor = mix(metalnessFactor, 1.0, sm * uWhite);`,
      );
  };
}

/** A pipe stub with a ribbed metal ferrule at its open end. */
function pipe(points: [number, number, number][], r: number, body: THREE.Material, metal: THREE.Material, dark: THREE.Material) {
  const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(...p)));
  const group = new THREE.Group();
  group.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 40, r, 32, false), body));
  const end = curve.getPoint(1);
  const dir = curve.getTangent(1).normalize();
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
  const ferrule = new THREE.Group();
  const sleeve = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.13, r * 1.13, r * 0.62, 40, 1, true), metal);
  ferrule.add(sleeve);
  for (const y of [-r * 0.22, r * 0.05]) {
    const rib = new THREE.Mesh(new THREE.TorusGeometry(r * 1.15, r * 0.05, 10, 48), metal);
    rib.rotation.x = Math.PI / 2;
    rib.position.y = y;
    ferrule.add(rib);
  }
  const lip = new THREE.Mesh(new THREE.TorusGeometry(r * 1.0, r * 0.15, 14, 48), metal);
  lip.rotation.x = Math.PI / 2;
  lip.position.y = r * 0.31;
  ferrule.add(lip);
  const mouth = new THREE.Mesh(new THREE.CircleGeometry(r * 0.92, 40), dark);
  mouth.rotation.x = -Math.PI / 2;
  mouth.position.y = r * 0.3;
  ferrule.add(mouth);
  ferrule.position.copy(end).addScaledVector(dir, -r * 0.18);
  ferrule.quaternion.copy(q);
  group.add(ferrule);
  return group;
}

function barcodeTexture() {
  const c = document.createElement('canvas');
  c.width = 512;
  c.height = 256;
  const g = c.getContext('2d');
  if (!g) return null;
  g.fillStyle = '#f4f4f2';
  g.fillRect(0, 0, 512, 256);
  g.strokeStyle = '#3a3d42';
  g.lineWidth = 6;
  g.strokeRect(8, 8, 496, 240);
  g.fillStyle = '#2a2d33';
  g.font = '28px monospace';
  g.fillText('MedVault record organ', 34, 62);
  g.fillText('Every claim cited.', 34, 98);
  let x = 40;
  let seed = 7;
  while (x < 470) {
    seed = (seed * 9301 + 49297) % 233280;
    const w = 3 + Math.floor((seed / 233280) * 9);
    g.fillRect(x, 124, w, 92);
    x += w + 3 + Math.floor(((seed * 7) % 100) / 25);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

export default function Heart3D({
  stage,
  interactive = true,
  reducedMotion = false,
  onReady,
}: {
  stage: React.MutableRefObject<HeartStage>;
  interactive?: boolean;
  reducedMotion?: boolean;
  onReady?: () => void;
}) {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.appendChild(renderer.domElement);
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    renderer.domElement.style.touchAction = interactive ? 'pan-y' : 'auto';

    const scene = new THREE.Scene();
    const pmrem = new THREE.PMREMGenerator(renderer);
    const env = buildStudio(pmrem);
    scene.environment = env;

    const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 50);
    camera.position.set(0, 0.1, 6.4);

    const key = new THREE.DirectionalLight('#ffffff', 1.2);
    key.position.set(3, 4, 5);
    scene.add(key, new THREE.AmbientLight('#ffffff', 0.2));

    const seamUniforms = { uWhite: { value: 0 } };
    const muscleMat = new THREE.MeshPhysicalMaterial({ ...CHROME, clearcoat: 0.8, clearcoatRoughness: 0.12, envMapIntensity: 1.25 });
    addSeams(muscleMat, seamUniforms);
    const vesselMat = new THREE.MeshPhysicalMaterial({ ...CHROME, clearcoat: 0.8, clearcoatRoughness: 0.12, envMapIntensity: 1.25 });
    const ferruleMat = new THREE.MeshStandardMaterial({ color: '#7d828b', metalness: 1, roughness: 0.22, envMapIntensity: 1.1, side: THREE.DoubleSide });
    const mouthMat = new THREE.MeshStandardMaterial({ color: '#1b1d21', metalness: 0.4, roughness: 0.6 });

    const heart = new THREE.Group();
    const muscle = buildMuscle(muscleMat);
    muscle.scale.setScalar(1.45);
    heart.add(muscle);

    // Pipe stubs: aorta (arching), pulmonary trunk, superior vena cava, two pulmonary veins
    const pipes: [[number, number, number][], number][] = [
      // aorta, arching over to the left
      [[[0.02, 0.3, -0.06], [0.08, 0.82, -0.02], [-0.04, 1.08, -0.06], [-0.26, 1.1, -0.1]], 0.15],
      // pulmonary trunk, in front, curving up and right
      [[[0.18, 0.28, 0.22], [0.32, 0.68, 0.26], [0.4, 0.98, 0.18]], 0.145],
      // superior vena cava
      [[[-0.36, 0.42, 0.08], [-0.42, 0.78, 0.06], [-0.44, 0.98, 0.05]], 0.12],
      // pulmonary veins, back right
      [[[0.48, 0.5, -0.2], [0.7, 0.66, -0.24], [0.84, 0.7, -0.24]], 0.09],
      [[[0.46, 0.34, -0.28], [0.74, 0.4, -0.32]], 0.085],
      // inferior vena cava, low on the left
      [[[-0.48, 0.0, -0.06], [-0.76, -0.14, -0.08]], 0.1],
    ];
    for (const [pts, r] of pipes) heart.add(pipe(pts, r, vesselMat, ferruleMat, mouthMat));

    // Barcode label on the lower right of the ventricles, visible once the heart is white
    const labelTex = barcodeTexture();
    const labelMat = new THREE.MeshStandardMaterial({ map: labelTex ?? undefined, transparent: true, opacity: 0, roughness: 0.6, metalness: 0, polygonOffset: true, polygonOffsetFactor: -2 });
    const label = new THREE.Mesh(new THREE.PlaneGeometry(0.34, 0.17), labelMat);
    heart.updateMatrixWorld(true);
    const ray = new THREE.Raycaster(new THREE.Vector3(1.6, -0.75, 2.4), new THREE.Vector3(-1.25, 0.05, -2.4).normalize());
    const hit = ray.intersectObject(muscle, false)[0];
    if (hit && hit.face) {
      const n = hit.face.normal.clone().transformDirection(muscle.matrixWorld);
      label.position.copy(heart.worldToLocal(hit.point.clone().addScaledVector(n, 0.012)));
      label.lookAt(heart.localToWorld(label.position.clone().add(n)));
      label.rotateZ(-0.35);
      heart.add(label);
    }

    heart.position.y = -0.02;
    heart.rotation.z = -0.1;

    const pivot = new THREE.Group();
    pivot.add(heart);
    scene.add(pivot);

    // Interaction: drag to rotate, with inertia back towards the scroll-driven pose
    let dragging = false;
    let lastX = 0;
    let lastY = 0;
    let userY = 0;
    let userX = 0;
    let velY = 0;
    const onDown = (e: PointerEvent) => {
      if (!interactive) return;
      dragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
      renderer.domElement.setPointerCapture(e.pointerId);
      host.style.cursor = 'grabbing';
    };
    const onMove = (e: PointerEvent) => {
      if (!dragging) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX;
      lastY = e.clientY;
      velY = dx * 0.008;
      userY += velY;
      userX = Math.max(-0.6, Math.min(0.6, userX + dy * 0.006));
    };
    const onUp = () => {
      dragging = false;
      host.style.cursor = interactive ? 'grab' : '';
    };
    renderer.domElement.addEventListener('pointerdown', onDown);
    renderer.domElement.addEventListener('pointermove', onMove);
    renderer.domElement.addEventListener('pointerup', onUp);
    renderer.domElement.addEventListener('pointercancel', onUp);
    if (interactive) host.style.cursor = 'grab';

    const resize = () => {
      const w = host.clientWidth || 1;
      const h = host.clientHeight || 1;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    resize();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(resize) : null;
    ro?.observe(host);

    const tmp = new THREE.Color();
    let raf = 0;
    let visible = true;
    const io = typeof IntersectionObserver !== 'undefined' ? new IntersectionObserver(([e]) => (visible = e.isIntersecting)) : null;
    io?.observe(host);

    const clock = new THREE.Clock();
    let readySent = false;
    const frame = () => {
      raf = requestAnimationFrame(frame);
      if (!visible) return;
      const t = clock.getElapsedTime();
      const s = stage.current;

      // Material: chrome → frosted white
      const w = Math.min(1, Math.max(0, s.white));
      for (const m of [muscleMat, vesselMat]) {
        m.color.copy(tmp.copy(CHROME.color).lerp(WHITE.color, w));
        m.metalness = CHROME.metalness + (WHITE.metalness - CHROME.metalness) * w;
        m.roughness = CHROME.roughness + (WHITE.roughness - CHROME.roughness) * w;
        m.clearcoat = 0.8 * (1 - w) + 0.1 * w;
        // matte plastic barely reflects the studio, so it stays neutral white rather than picking up blue
        m.envMapIntensity = 1.25 * (1 - w) + 0.45 * w;
      }
      seamUniforms.uWhite.value = w;
      labelMat.opacity = Math.max(0, (w - 0.6) / 0.4);

      // Heartbeat: a lub-dub every ~1.1 s
      const beatT = (t % 1.1) / 1.1;
      const beat = reducedMotion ? 0 : Math.exp(-Math.pow((beatT - 0.08) / 0.04, 2)) * 0.03 + Math.exp(-Math.pow((beatT - 0.28) / 0.05, 2)) * 0.018;

      if (!dragging) {
        velY *= 0.93;
        userY += velY;
        userY *= 0.985; // drift back to the scroll pose
        userX *= 0.95;
      }
      // Gentle sway rather than a full spin, so the front with its seams stays mostly in view
      const idle = reducedMotion ? 0 : Math.sin(t * 0.35) * 0.45;
      pivot.rotation.y = -0.35 + idle + s.spin + userY;
      pivot.rotation.x = 0.12 + userX;
      pivot.scale.setScalar(s.scale * (1 + beat));
      const vh = 2 * Math.tan((camera.fov * Math.PI) / 360) * camera.position.z;
      pivot.position.set((s.x * vh * camera.aspect) / 2, (s.y * vh) / 2, 0);

      renderer.render(scene, camera);
      if (!readySent) {
        readySent = true;
        onReady?.();
      }
    };
    frame();

    return () => {
      cancelAnimationFrame(raf);
      ro?.disconnect();
      io?.disconnect();
      renderer.domElement.removeEventListener('pointerdown', onDown);
      renderer.domElement.removeEventListener('pointermove', onMove);
      renderer.domElement.removeEventListener('pointerup', onUp);
      renderer.domElement.removeEventListener('pointercancel', onUp);
      scene.traverse((o) => (o as THREE.Mesh).geometry?.dispose?.());
      [muscleMat, vesselMat, ferruleMat, mouthMat, labelMat].forEach((m) => m.dispose());
      labelTex?.dispose();
      env.dispose();
      pmrem.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [stage, interactive, reducedMotion, onReady]);

  return <div ref={hostRef} className="h-full w-full" aria-label="3D heart. Drag to rotate." role="img" />;
}
