
// class for the walkable background arena/scene
class WalkableBackground {

    // constructor method
    constructor(image, x_s, x_e, y_s, y_e, disco_images) {
        this.image = image;
        this.x_start = x_s;
        this.x_end = x_e;
        this.y_start = y_s;
        this.y_end = y_e;
        this.dance_mode = false;
        this.disco_images = disco_images;
        this.disco_start_pos = -70;
        this.disco_final_pos = 50;
        this.disco_position = this.disco_start_pos;
    }

    // get index of disco animation
    get_index() {
        return Math.floor((frameCount / 5) % this.disco_images.length);
    }

    // draw the background
    draw() {
        background(this.image);

        // in dance mode add color filter for lighting
        if (this.dance_mode) {
            push();
            // hsb color mode to easily move in the hue
            colorMode(HSB);
            // map disco ball pos with regards to start and end positions
            // to also gradually introduce the color sweep
            let disco_progress = map(
                this.disco_position, 
                this.disco_start_pos,
                this.disco_final_pos,
                0,
                1
            )
            fill(frameCount % 360, 100, 100, 0.5 * disco_progress * (sin(frameCount / 5)/2 + 0.5));
            rect(0, 0, width, height);
            pop();
        }

        // when in dance mode, lower disco balls
        if (this.dance_mode && this.disco_position != this.disco_final_pos) {
            this.disco_position++;
        } else if (!this.dance_mode && this.disco_position != this.disco_start_pos) {
            this.disco_position--;
        }
        push();
        imageMode(CENTER);
        image(this.disco_images[this.get_index()], Math.round(0.05 * width), this.disco_position);
        image(this.disco_images[this.get_index()], Math.round(0.95 * width), this.disco_position);
        pop();
    }


    // helper to bounce an object of border 
    // of walkable zone
    bounce(x, y, x_dir, y_dir) {
        if (x < this.x_start) {
            x_dir = abs(x_dir);
        }
        if (x > this.x_end) {
            x_dir = -abs(x_dir);
        }
        if (y < this.y_start) {
            y_dir = abs(y_dir);
        }
        if (y > this.y_end) {
            y_dir = -abs(y_dir);
        }
        return [x_dir, y_dir];
    }

    // helper to get random x position in walkable zone
    random_walkable_x() {
        return random(this.x_start, this.x_end);
    }

    // helper to get random y position in walkable zone
    random_walkable_y() {
        return random(this.y_start, this.y_end);
    }
}