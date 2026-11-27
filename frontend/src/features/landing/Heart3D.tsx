import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { MarchingCubes } from 'three/examples/jsm/objects/MarchingCubes.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

/**
 * A procedural anatomical heart, rendered in real time.
 *
 * The muscle is a metaball field (marching cubes): overlapping spheres for the two ventricles,
 * the atria and a tapered apex. The great vessels are swept tubes with metal end caps.
 * `progress` (0 → 1) is driven by page scroll: chrome → matte white → shrunk into the chest.
 * Dragging rotates the heart; it settles back with inertia.
 */

export interface HeartStage {
  /** 0..1 how far chrome has turned to matte white */
  white: number;
  /** uniform scale multiplier */
  scale: number;
  /** offset in canvas-relative units (-1..1) */
  x: number;
  y: number;
  /** extra spin from scroll, radians */
  spin: number;
}

const CHROME = { color: new THREE.Color('#dfe3ea'), metalness: 1, roughness: 0.14 };
const WHITE = { color: new THREE.Color('#f1f1ef'), metalness: 0.02, roughness: 0.5 };

function buildMuscle(material: THREE.Material) {
  const mc = new MarchingCubes(56, material, false, false, 60000);
  mc.isolation = 80;
  mc.reset();
  // [x, y, z, strength] in the 0..1 field; y is up, apex at the bottom
  const balls: [number, number, number, number][] = [
    [0.6, 0.2, 0.5, 0.32], // apex, tipped to the patient's left
    [0.57, 0.29, 0.5, 0.75],
    [0.52, 0.4, 0.5, 1.15], // ventricular mass
    [0.67, 0.44, 0.46, 0.95], // left ventricle
    [0.36, 0.45, 0.56, 0.95], // right ventricle
    [0.62, 0.53, 0.48, 0.7],
    [0.38, 0.53, 0.54, 0.7],
    [0.5, 0.42, 0.38, 0.8], // depth, back
    [0.5, 0.42, 0.62, 0.8], // depth, front
    [0.48, 0.55, 0.5, 1.05], // base
    [0.35, 0.6, 0.54, 0.6], // right atrium
    [0.63, 0.61, 0.42, 0.55], // left atrium
    [0.29, 0.55, 0.62, 0.22], // auricle
  ];
  for (const [x, y, z, s] of balls) mc.addBall(x, y, z, s, 12);
  mc.update();
  return mc;
}

function tube(points: [number, number, number][], radius: number, material: THREE.Material) {
  const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(...p)));
  const geo = new THREE.TubeGeometry(curve, 48, radius, 28, false);
  return { mesh: new THREE.Mesh(geo, material), curve };
}

function cap(curve: THREE.CatmullRomCurve3, radius: number, material: THREE.Material) {
  const end = curve.getPoint(1);
  const tangent = curve.getTangent(1);
  const g = new THREE.CylinderGeometry(radius * 1.14, radius * 1.14, radius * 0.7, 32, 1, true);
  const ring = new THREE.Mesh(g, material);
  ring.position.copy(end);
  ring.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tangent.normalize());
  const lip = new THREE.Mesh(new THREE.TorusGeometry(radius * 1.14, radius * 0.12, 12, 40), material);
  lip.position.copy(end);
  lip.quaternion.copy(ring.quaternion).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 2));
  return [ring, lip];
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
    renderer.toneMappingExposure = 1.05;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.appendChild(renderer.domElement);
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    renderer.domElement.style.touchAction = interactive ? 'pan-y' : 'auto';

    const scene = new THREE.Scene();
    const pmrem = new THREE.PMREMGenerator(renderer);
    const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = env;

    const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 50);
    camera.position.set(0, 0.05, 6.2);

    const key = new THREE.DirectionalLight('#ffffff', 1.6);
    key.position.set(3, 4, 5);
    scene.add(key, new THREE.AmbientLight('#ffffff', 0.25));

    const muscleMat = new THREE.MeshPhysicalMaterial({ ...CHROME, clearcoat: 0.6, clearcoatRoughness: 0.2, envMapIntensity: 1.3 });
    const vesselMat = new THREE.MeshPhysicalMaterial({ ...CHROME, clearcoat: 0.6, clearcoatRoughness: 0.2, envMapIntensity: 1.3, side: THREE.DoubleSide });
    const capMat = new THREE.MeshStandardMaterial({ color: '#8b9099', metalness: 1, roughness: 0.28, envMapIntensity: 1.2, side: THREE.DoubleSide });

    const heart = new THREE.Group();
    const muscle = buildMuscle(muscleMat);
    muscle.scale.setScalar(1.15);
    heart.add(muscle);

    const vessels: [[number, number, number][], number][] = [
      // aorta: rises behind the pulmonary trunk and arches over to the left
      [[[0.0, 0.05, -0.05], [0.04, 0.62, -0.02], [-0.08, 0.92, -0.08], [-0.34, 0.88, -0.12], [-0.44, 0.6, -0.16]], 0.15],
      // pulmonary trunk: in front, heading up and to the right
      [[[0.12, 0.05, 0.22], [0.24, 0.5, 0.26], [0.42, 0.76, 0.16]], 0.14],
      // superior vena cava
      [[[-0.36, 0.3, 0.1], [-0.4, 0.64, 0.08], [-0.41, 0.98, 0.06]], 0.11],
      // arch branches
      [[[-0.14, 0.9, -0.06], [-0.15, 1.14, -0.03]], 0.06],
      [[[-0.28, 0.9, -0.1], [-0.31, 1.12, -0.07]], 0.055],
      // pulmonary vein on the left side
      [[[0.5, 0.42, -0.22], [0.82, 0.5, -0.3]], 0.07],
    ];
    for (const [pts, r] of vessels) {
      const { mesh, curve } = tube(pts, r, vesselMat);
      heart.add(mesh, ...cap(curve, r, capMat));
    }
    heart.position.y = -0.12;
    heart.rotation.z = -0.12;

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

      // Material: chrome → matte white
      const w = Math.min(1, Math.max(0, s.white));
      for (const m of [muscleMat, vesselMat]) {
        m.color.copy(tmp.copy(CHROME.color).lerp(WHITE.color, w));
        m.metalness = CHROME.metalness + (WHITE.metalness - CHROME.metalness) * w;
        m.roughness = CHROME.roughness + (WHITE.roughness - CHROME.roughness) * w;
      }

      // Heartbeat: a lub-dub every ~1.1 s
      const beatT = (t % 1.1) / 1.1;
      const beat = reducedMotion ? 0 : Math.exp(-Math.pow((beatT - 0.08) / 0.04, 2)) * 0.035 + Math.exp(-Math.pow((beatT - 0.28) / 0.05, 2)) * 0.02;

      if (!dragging) {
        velY *= 0.93;
        userY += velY;
        userY *= 0.985; // drift back to the scroll pose
        userX *= 0.95;
      }
      const idle = reducedMotion ? 0 : t * 0.18;
      pivot.rotation.y = idle + s.spin + userY;
      pivot.rotation.x = userX;
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
      scene.traverse((o) => {
        const mesh = o as THREE.Mesh;
        mesh.geometry?.dispose?.();
      });
      [muscleMat, vesselMat, capMat].forEach((m) => m.dispose());
      env.dispose();
      pmrem.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [stage, interactive, reducedMotion, onReady]);

  return <div ref={hostRef} className="h-full w-full" aria-label="3D heart. Drag to rotate." role="img" />;
}
