async function loadImages(files) {
    let images = []
    for (let i = 0; i < files.length; i++) {
        images.push(await loadImage(files[i]))
    }
    return images
}

function loadZombie(n) {
    let dance_files = [];
    for (let j = 0; j < 8; j++) {
        dance_files.push(`assets/zombies/zombie${n}/zombie${n}_dance${j}.png`);
    }
    return dance_files;
}