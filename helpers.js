// array to map direction index to name
// used for the help method below
// index i is the direction at angle 45 * i degrees (same order as CARD_TO_DIR)
DIRS = ["E", "SE", "S", "SW", "W", "NW", "N", "NE"]

// helper function to load multiple images
async function loadImages(files) {
    let images = []
    for (let i = 0; i < files.length; i++) {
        images.push(await loadImage(files[i]))
    }
    return images
}

// helper to load disco images
async function loadDisco() {
    let images = [];
    for (let j = 0; j < 8; j++) {
        images.push(await loadImage(`assets/disco_ball/disco_ball_${j}.png`));
    }
    return images;
}

// helper function to load a zombie
async function loadZombie(n) {

    // load all dances

    let dances = [];
    for (let d = 1; d <= NUM_DANCES; d++) {
        let dance_files = [];
        for (let j = 0; j < 8; j++) {
            dance_files.push(`assets/zombies/zombie${n}/dances/dance${d}/zombie${n}_dance${d}_${j}.png`);
        }
        dances.push(await loadImages(dance_files));
    }

    // load all walking directions

    let dirs = [];
    for (let a = 0; a < 8; a++) {
        let dir_files = [];
        for (let j = 0; j < 6; j++) {
            dir_files.push(`assets/zombies/zombie${n}/walk/${DIRS[a]}/zombie${n}_walk_${DIRS[a]}_${j}.png`);
        }
        dirs.push(await loadImages(dir_files));
    }

    return [dances, dirs];
}

// random integer method
function randint(start, end) {
    return Math.floor(random(start, end));
}