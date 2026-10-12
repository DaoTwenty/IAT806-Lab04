let frames = [];
let grid = {width: 50, height: 50};
let zombies = []
let NUM_ZOMBIES = 6;
let SPEED = 10;
let SIGMA = 20;
let ROTATION_SPEED = 0.5;
let ROTATION_TIME = 250;

async function setup() {
    createCanvas(800, 800);

    for (let i = 1; i < NUM_ZOMBIES; i++) {
        frames.push(await loadImages(loadZombie(i)));
    }

    for (let x = 0; x < width; x += grid.width) {
        for (let y = 0; y < height; y += grid.height) {
            let zombie_idx = Math.floor(random(0, frames.length));
            zombies.push({
                animation: new FramesAnimation(
                        frames[zombie_idx],
                        SPEED + Math.floor(random(-5, 5)),
                        x + grid.width / 2,
                        y + grid.height / 2,
                        0,
                        grid.height,
                        true,
                        Math.floor(random(0, frames[zombie_idx].length))
                ),
                clicked: -1
            });
        }
    }
}

function draw() {
    background(255);

    for (let i = 0; i < zombies.length; i++) {
        let new_size = min(1,max(Math.exp( -((zombies[i].animation.x - mouseX)**2 + (zombies[i].animation.y - mouseY)**2) / (2 * SIGMA**2) / Math.sqrt(2 * Math.PI * SIGMA**2)), 0.5));
        zombies[i].animation.set_size(grid.height * new_size, true);
        if (zombies[i].clicked != -1) {
            if (frameCount - zombies[i].clicked < ROTATION_TIME) {
                zombies[i].animation.rotate(ROTATION_SPEED * Math.exp(-1 * (frameCount - zombies[i].clicked)**2 / ROTATION_TIME**2));
            } else {
                zombies[i].clicked = -1;
            }
        }
        zombies[i].animation.draw();
    }
}

function mouseClicked() {
    for (let i = 0; i < zombies.length; i++) {
        if (zombies[i].animation.is_clicked()) {
            zombies[i].clicked = frameCount;
        }
    }
}
