// convert direction index to a unit vector
// index i points at angle 45 * i degrees (0 = east, clockwise because y points down)
// 1/sqrt(2) makes each direction have same speed amp
let CARD_TO_DIR = [
    [1, 0],                               // 0   E
    [1/Math.sqrt(2), 1/Math.sqrt(2)],     // 45  SE
    [0, 1],                               // 90  S
    [-1/Math.sqrt(2), 1/Math.sqrt(2)],    // 135 SW
    [-1, 0],                              // 180 W
    [-1/Math.sqrt(2), -1/Math.sqrt(2)],   // 225 NW
    [0, -1],                              // 270 N
    [1/Math.sqrt(2), -1/Math.sqrt(2)]     // 315 NE
]

class WalkingDancingAnimation {

    // takes the image files and the speed. Images are drawn at their own size, never resized
    constructor(
        dance_images, 
        walk_images, 
        direction, 
        speed, 
        walk_speed, 
        x, 
        y, 
        rotation, 
        size, 
        isHeight, 
        initFrame,
        bounceMethod
    ) {
        // frames for the dancing
        this.dance_images = dance_images;
        // frames for the walking
        this.walk_images = walk_images;
        // direction is index of all 8 cardinal/intercardinal directions
        this.direction = direction;
        this.cardinal_direction = CARD_TO_DIR[this.direction];
        // original speed
        this.og_speed = speed;
        this.speed = speed;
        // initial pos
        this.x = x;
        this.y = y;
        // walking speed
        this.walk_speed = walk_speed;
        // start frame for animation
        this.index = initFrame;
        // because of varying speed, we need to update a phase
        // that will be used to infer the frame index
        this.phase = initFrame;
        // is zombie still alive
        this.active = true;
        // init rotation
        this.rotation = rotation;
        // method use to bounce on border
        this.bounceMethod = bounceMethod;

        // size is keeps aspect ratio intact
        if (isHeight) {
            this.height = size;
            this.width = Math.floor(this.height * this.dance_images[0].width / this.dance_images[0].height);
        } else {
            this.width = size;
            this.height = Math.floor(this.width * this.dance_images[0].height / this.dance_images[0].width);
        }
        this.frozen = false;
        this.dancing = false;

        // bool to indicate the zombie is 
        // walking to its dance position
        this.on_a_mission = false;
    }

    set_size(size, isHeight) {
        if (isHeight) {
            this.height = size;
            this.width = Math.floor(this.height * this.dance_images[0].width / this.dance_images[0].height);
        } else {
            this.width = size;
            this.height = Math.floor(this.width * this.dance_images[0].height / this.dance_images[0].width);
        }
    }

    set_speed(speed) {
        this.speed = speed;
    }

    // freeze zombie
    freeze() {
        this.frozen = true;
    }

    unfreeze() {
        this.frozen = false;
    }

    dance() {
        this.dancing = true;
    }

    walk() {
        this.dancing = false;
    }

    get_index() {
        if (this.frozen == false) {
            this.phase += 1/this.speed;
            if (this.dancing) {
                this.index = Math.floor(this.phase % this.dance_images.length);
            } else {
                this.index = Math.floor(this.phase % this.walk_images[this.direction].length);
            }
        }
    }

    move(x, y) {
        this.x += x;
        this.y += y;
    }

    move_to(x, y) {
        this.x = x;
        this.y = y
    }

    // method to make zombie walk to given
    // position then dance
    go_to_and_dance(x_target, y_target) {
        this.x_target = x_target;
        this.y_target = y_target;
        this.dy = this.y_target - this.y;
        this.dx = this.x_target - this.x;
        // how to move diagonally to target
        this.diagonal = min(abs(this.dy), abs(this.dx));
        // direction index of the diagonal movement from the signs of dx and dy
        if (this.dx >= 0 && this.dy >= 0) {
            this.diagonal_direction = 1;   // SE
        } else if (this.dx < 0 && this.dy >= 0) {
            this.diagonal_direction = 3;   // SW
        } else if (this.dx < 0 && this.dy < 0) {
            this.diagonal_direction = 5;   // NW
        } else {
            this.diagonal_direction = 7;   // NE
        }
        // how to move straight to target
        // is along x if x has more distance to cover, otherwise along y
        this.straight = abs(abs(this.dx) - abs(this.dy));
        if (abs(this.dx) > abs(this.dy)) {
            // going east or west
            this.straight_direction = this.dx >= 0 ? 0 : 4; 
        } else {
            // going north or south
            this.straight_direction = this.dy >= 0 ? 2 : 6;  
        }

        // we randomly decide whether to do diag or straight movement first
        this.diag_first = random(0,1) > 0.5;

        this.on_a_mission = true;
    }

    rotate(angle) {
        this.rotation += angle;
    }

    rotate_to(angle) {
        this.rotation = angle;
    }

    update_pos() {
        if (!this.on_a_mission) {

            // randomly change direction
            if (!this.dancing && random(0,1) < 0.01) {
                this.direction += 2*randint(0, 2) - 1;
                this.direction = (this.direction + 8) % 8;
                this.cardinal_direction = CARD_TO_DIR[this.direction];
            }

            // update direction with potential bounce of borders
            this.cardinal_direction = this.bounceMethod(
                this.x, 
                this.y, 
                this.cardinal_direction[0], 
                this.cardinal_direction[1]
            );
        } else {
            //check if we are close
            if (this.diagonal <= 0 && this.straight <= 0) {
                this.x = this.x_target;
                this.y = this.y_target;
                this.on_a_mission = false;
                this.dancing = true;
                return;
            }

            // set the direction to either diagonal or straight
            if (this.diagonal > 0 && (this.diag_first || this.straight <= 0)) {   
                this.direction = this.diagonal_direction;

                //update diagonal
                this.diagonal -= this.walk_speed / Math.sqrt(2);
            } else if (this.straight > 0) {
                this.direction = this.straight_direction;

                //update straight
                this.straight -= this.walk_speed;
            }
            this.cardinal_direction = CARD_TO_DIR[this.direction];
        }
        // update position with speed when walking
        this.x += this.walk_speed * this.cardinal_direction[0];
        this.y += this.walk_speed * this.cardinal_direction[1];

        // adjust index with new cardinal dir
        this.direction = CARD_TO_DIR.findIndex(
            (dir) => {
                return dir[0] == this.cardinal_direction[0] && dir[1] == this.cardinal_direction[1]
            }
        );
    }

    draw() {
        if (this.active == true) {
            push();
            imageMode(CENTER);
            this.get_index();
            translate(this.x, this.y);
            if (!this.dancing) {
                // if walking retrieve appropriate frames
                image(this.walk_images[this.direction][this.index], 0, 0, this.width, this.height);
                // update position
                this.update_pos();
            } else {
                // use dancing frames
                rotate(this.rotation);
                image(this.dance_images[this.index], 0, 0, this.width, this.height);
            }
            pop();
        } 
    }

    is_clicked() {
        // check if in ellipse of the zombie (half the width and height are the radii)
        if ((mouseX - this.x)**2/(this.width/2)**2 + (mouseY - this.y)**2/(this.height/2)**2 <= 1) {
            return true;
        } else {
            return false;
        }
    }
}
