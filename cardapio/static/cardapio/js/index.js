import * as THREE from "three";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";
import { TGALoader } from "three/addons/loaders/TGALoader.js";

const container = document.getElementById('hero-canvas');
if (!container) throw new Error('hero-canvas not found');

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x000000, 0);
container.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
camera.position.z = 22;

scene.add(new THREE.AmbientLight(0xfff5e3, 0.9));
const sun = new THREE.DirectionalLight(0xffddb0, 1.6);
sun.position.set(-6, 8, 10);
scene.add(sun);
const top = new THREE.DirectionalLight(0xffe8c8, 0.6);
top.position.set(2, 10, 4);
scene.add(top);

const urls = window.COOKIE_MODEL_URLS || {};
const objects = [];
const tgaLoader = new TGALoader();
const objLoader = new OBJLoader();

const isMobile = window.innerWidth < 768;

// Posições fixas: [x, y, z, rotX, rotY, rotZ, floatSpeed, floatAmp, floatOffset]
const COOKIE_SPAWNS = isMobile ? [
    [ 2.0,  3.7,  0,    0.4,  0.8,  0.2,  0.3, 0.25, 0.0 ],
    [ 3.0,  6.0,  0,    1.2,  2.1,  0.5,  0.4, 0.2,  1.5 ],
] : [
    [ 13,   2.5,  0,    0.4,  0.8,  0.2,  0.3, 0.4, 0.0 ],
    [ 11,  -1.5, -1,    1.2,  2.1,  0.5,  0.4, 0.3, 1.0 ],
    [  5,   5.0,  1,    2.5,  1.0,  1.8,  0.5, 0.5, 2.1 ],
    [  7,   0.5, -2,    0.9,  3.2,  0.3,  0.35,0.45,3.5 ],
];
const CRUMB_SPAWNS = isMobile ? [
    [ 1.2,  5.1,  0.3,  1.0,  0.5,  2.0,  0.5, 0.2, 1.0 ],
    [ 3.6,  3.3,  0.4,  2.2,  1.8,  0.8,  0.45,0.25,1.8 ],
    [ 1.6,  3.0, -0.3,  0.7,  2.8,  1.5,  0.55,0.35,3.0 ],
    [ 4.0,  5.7,  0.5,  1.8,  0.4,  2.5,  0.4, 0.4, 4.2 ],
] : [
    [ 11,   4.5,  0.5,  1.0,  0.5,  2.0,  0.6, 0.3, 0.5 ],
    [ 13,  -0.5,  0.5,  2.2,  1.8,  0.8,  0.45,0.25,1.8 ],
    [  8,   1.8, -1,    0.7,  2.8,  1.5,  0.55,0.35,3.0 ],
    [  9.5,-2.5,  1,    1.8,  0.4,  2.5,  0.4, 0.4, 4.2 ],
];

function loadTextures(texUrls, onReady) {
    const albedo    = tgaLoader.load(texUrls.albedo);
    const normal    = tgaLoader.load(texUrls.normal);
    const roughness = tgaLoader.load(texUrls.roughness);
    albedo.colorSpace = THREE.SRGBColorSpace;
    onReady(new THREE.MeshStandardMaterial({
        map: albedo, normalMap: normal, roughnessMap: roughness,
        roughness: 1.0, metalness: 0.0,
    }));
}

function spawnObject(url, mat, scaleTarget, spawn) {
    const [x, y, z, rotX, rotY, rotZ, floatSpeed, floatAmp, floatOffset] = spawn;
    objLoader.load(url, (obj) => {
        obj.traverse(child => { if (child.isMesh) child.material = mat; });

        const box = new THREE.Box3().setFromObject(obj);
        const size = box.getSize(new THREE.Vector3());
        obj.scale.setScalar(scaleTarget / Math.max(size.x, size.y, size.z));

        obj.position.set(x, y, z);
        obj.rotation.set(rotX, rotY, rotZ);

        obj.userData = {
            baseY: y,
            floatSpeed, floatAmp, floatOffset,
            rotX: 0.0002, rotY: 0.0015, rotZ: 0.0002,
            dragging: false,
        };

        scene.add(obj);
        objects.push(obj);
    });
}

loadTextures(urls.textures || {}, (mat) => {
    const cookieUrls = isMobile ? (urls.cookies || []).slice(0, 2) : (urls.cookies || []);
    const crumbUrls  = isMobile ? (urls.crumbs  || []).slice(0, 4) : (urls.crumbs  || []);

    cookieUrls.forEach((url, i) => {
        spawnObject(url, mat, isMobile ? 1.8 : 4.0, COOKIE_SPAWNS[i % COOKIE_SPAWNS.length]);
    });
    crumbUrls.forEach((url, i) => {
        spawnObject(url, mat.clone(), isMobile ? 0.12 : 0.25, CRUMB_SPAWNS[i % CRUMB_SPAWNS.length]);
    });
});

// ── Drag interaction ──────────────────────────────────────────────
const raycaster = new THREE.Raycaster();
const dragPlane = new THREE.Plane();
const dragOffset = new THREE.Vector3();
const intersectPt = new THREE.Vector3();
let dragging = null;

function allMeshes() {
    const meshes = [];
    objects.forEach(obj => obj.traverse(c => { if (c.isMesh) meshes.push(c); }));
    return meshes;
}

function ndcFromEvent(e) {
    const src = e.touches ? e.touches[0] : e;
    const rect = renderer.domElement.getBoundingClientRect();
    return new THREE.Vector2(
        ((src.clientX - rect.left) / rect.width)  *  2 - 1,
        ((src.clientY - rect.top)  / rect.height) * -2 + 1,
    );
}

function findRoot(mesh) {
    let obj = mesh;
    while (obj.parent && obj.parent !== scene) obj = obj.parent;
    return obj;
}

function onPointerDown(e) {
    raycaster.setFromCamera(ndcFromEvent(e), camera);
    const hits = raycaster.intersectObjects(allMeshes());
    if (!hits.length) return;

    dragging = findRoot(hits[0].object);
    dragging.userData.dragging = true;

    dragPlane.setFromNormalAndCoplanarPoint(
        camera.getWorldDirection(new THREE.Vector3()).negate(),
        dragging.position,
    );
    raycaster.ray.intersectPlane(dragPlane, intersectPt);
    dragOffset.subVectors(dragging.position, intersectPt);

    renderer.domElement.style.cursor = 'grabbing';
    e.preventDefault();
}

function onPointerMove(e) {
    raycaster.setFromCamera(ndcFromEvent(e), camera);

    if (dragging) {
        raycaster.ray.intersectPlane(dragPlane, intersectPt);
        dragging.position.copy(intersectPt.add(dragOffset));
        dragging.userData.baseY = dragging.position.y;
        return;
    }

    const hits = raycaster.intersectObjects(allMeshes());
    renderer.domElement.style.cursor = hits.length ? 'grab' : 'default';
}

function onPointerUp() {
    if (!dragging) return;
    dragging.userData.dragging = false;
    dragging.userData.baseY = dragging.position.y;
    dragging = null;
    renderer.domElement.style.cursor = 'default';
}

const el = renderer.domElement;
el.addEventListener('mousedown',  onPointerDown, { passive: false });
el.addEventListener('mousemove',  onPointerMove);
el.addEventListener('mouseup',    onPointerUp);
el.addEventListener('mouseleave', onPointerUp);
el.addEventListener('touchstart', onPointerDown, { passive: false });
el.addEventListener('touchmove',  onPointerMove, { passive: false });
el.addEventListener('touchend',   onPointerUp);

// ── Resize ───────────────────────────────────────────────────────
function resize() {
    const w = container.clientWidth;
    const h = container.clientHeight;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
}
resize();
window.addEventListener('resize', resize);

// ── Render loop ──────────────────────────────────────────────────
function animate(t = 0) {
    requestAnimationFrame(animate);
    const time = t * 0.001;
    objects.forEach(obj => {
        const d = obj.userData;
        if (!d.dragging) {
            obj.position.y = d.baseY + Math.sin(time * d.floatSpeed + d.floatOffset) * d.floatAmp;
        }
        obj.rotation.x += d.rotX;
        obj.rotation.y += d.rotY;
        obj.rotation.z += d.rotZ;
    });
    renderer.render(scene, camera);
}
animate();
