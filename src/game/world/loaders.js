// One GLTF loader for every model in the game: a single Draco decoder (local /draco, its
// wasm fetched and compiled once) and the Meshopt decoder, shared by the environment and the cast.
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

let loader;
export function gltfLoader() {
  if (!loader) {
    const draco = new DRACOLoader().setDecoderPath('./draco/');
    draco.preload();                                   // start fetching the decoder with the first model
    loader = new GLTFLoader().setDRACOLoader(draco).setMeshoptDecoder(MeshoptDecoder);
  }
  return loader;
}
