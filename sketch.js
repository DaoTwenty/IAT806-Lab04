let frames = [];
let bg;
let backgrounds = [];
let bg_idx = 0;
let grid = {width: 72, height: 128};
let zombies = []
let NUM_ZOMBIES = 5;
let SPEED = 10;
let WALK_SPEED = 1;
let SIGMA = 20;
let ROTATION_SPEED = 0.5;
let ROTATION_TIME = 250;
// 3 different dance variations
let NUM_DANCES = 3

async function setup() {
     createCanvas(1280, 720);

    // load zombie frames
    for (let i = 1; i <= NUM_ZOMBIES; i++) {
        frames.push(await loadZombie(i));
    }

    backgrounds.push(await loadImage("assets/backgrounds/airport.png"));
    backgrounds.push(await loadImage("assets/backgrounds/empty_mall.png"));
    backgrounds.push(await loadImage("assets/backgrounds/giant_picnic.png"));
    backgrounds.push(await loadImage("assets/backgrounds/street_intersection.png"));

    // load background arena
    bg = new WalkableBackground(
        backgrounds[bg_idx], 
        0.1 * width, 
        0.9 * width, 
        0.1 * height, 
        0.9 * height,
        await loadDisco()
    );

    // create the zombies on a grid using a dict, but start with random pos
    let i;
    for (let x = 0.1 * width; x <= 0.9 * width - grid.width; x += grid.width) {
        for (let y = 0.1 * height; y <= 0.9 * height - grid.height; y += grid.height) {
            let zombie_idx = Math.floor(random(0, frames.length));
            i = x * width + y;
            zombies.push({
                // the actual zombie animation
                animation: new WalkingDancingAnimation(
                    // alternate between all dances in grid
                    frames[zombie_idx][0][i%NUM_DANCES],
                    frames[zombie_idx][1],
                    Math.floor(random(0, 8)),
                    SPEED + Math.floor(random(-5, 5)),
                    WALK_SPEED,
                    bg.random_walkable_x(),
                    bg.random_walkable_y(),
                    0,
                    grid.height,
                    true,
                    Math.floor(random(0, frames[zombie_idx][0][i%NUM_DANCES].length)),
                    (...x) => {return bg.bounce(...x)}
                ),
                // to track clicked zombies and time when clicked
                clicked: -1,
                // grid position
                x_grid: x + grid.width / 2,
                y_grid: y + grid.height / 2
            });
        }
    }
}

function draw() {
    bg.draw();

    for (let i = 0; i < zombies.length; i++) {
        // distance between dancing zombie and mouse
        let distance = dist(zombies[i].animation.x, zombies[i].animation.y, mouseX, mouseY);
        // size is a normal distribution centered around mouse
        let new_size = min(1,max(Math.exp( -(distance**2) / (2 * SIGMA**2) / Math.sqrt(2 * Math.PI * SIGMA**2)), 0.5));
        zombies[i].animation.set_size(grid.height * new_size, true);
        // speed is mapped to 100-200% of original speed
        // only affected if dancing
        if (zombies[i].animation.dancing) {
            let speed = map(new_size, 0.5, 1, zombies[i].animation.og_speed, zombies[i].animation.og_speed / 2);
            zombies[i].animation.set_speed(speed);
        }
        if (zombies[i].clicked != -1) {
            // clicked zombies spin at a decreasing rate for set time
            if (frameCount - zombies[i].clicked < ROTATION_TIME) {
                zombies[i].animation.rotate(ROTATION_SPEED * Math.exp(-1 * (frameCount - zombies[i].clicked)**2 / ROTATION_TIME**2));
            } else {
                zombies[i].clicked = -1;
            }
        }
        zombies[i].animation.draw();
    }

    // draw the search beams
    bg.draw_beam();

}

function mouseClicked() {
    // record when each zombie is clicked 
    for (let i = 0; i < zombies.length; i++) {
        if (zombies[i].animation.is_clicked()) {
            zombies[i].clicked = frameCount;
        }
    }
}

function keyPressed(event) {

    // change background
    if (key == 'b') {
        bg_idx += 1;
        bg_idx = bg_idx % 4;
        bg.image = backgrounds[bg_idx];
    }

    // when press 'd', zombies get in line to dance
    if (key == 'd') {
        bg.dance_mode = true;
        for (let z = 0; z < zombies.length; z++) {
            // send zombies to their grid position
            // that was saved in the zombies dict object
            if (!zombies[z].on_a_mission) {
                zombies[z].animation.go_to_and_dance(
                    zombies[z].x_grid,
                    zombies[z].y_grid
                )
            }
        }
    }
    if (key == 'w') {
        bg.dance_mode = false;
        for (let z = 0; z < zombies.length; z++) {
            // send zombies to their grid position
            // that was saved in the zombies dict object
            zombies[z].animation.dancing = false;
            // reset them upright
            zombies[z].animation.rotate_to(0);
        }
    }
}
