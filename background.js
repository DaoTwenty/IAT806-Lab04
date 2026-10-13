
let x_a;
let y_a;
let D_prime;
let D;
let x_0;
let y_0;
let x_1;
let y_1;

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

    draw_beam() {
        // if mouse is inside of screen
        // otherwise we dont draw the beams
        if (mouseX >= 0 && mouseX < width && mouseY >= 0 && mouseY < height) {
            push();
            colorMode(RGB);
            noStroke();
            fill(255, 255, 255, 130);

            let a = 50;
            let b = 25;

            // search beam is a ellipse on the ground
            ellipse(
                mouseX,
                mouseY,
                2*a,
                2*b
            );

            push();
            fill(255, 255, 255, 60);
            // same ellipse but for clipping the triangle,
            // inverted so the triangle is cut out where the ellipse is
            clip(() => {
                ellipse(
                    mouseX,
                    mouseY,
                    2*a,
                    2*b
                );
            }, { invert: true });

            // using some math we calculate tangents to the ellpise
            // from the disco ball positions
            y_a = this.disco_position - mouseY;
            x_a = 0.05 * width - mouseX;
            D_prime = b**2 * x_a**2 + a**2 * y_a**2;
            D = D_prime - a**2 * b**2;

            if (D > 0) {

                x_0 = a**2 * (b**2 * x_a + y_a * Math.sqrt(D))/D_prime
                x_1 = a**2 * (b**2 * x_a - y_a * Math.sqrt(D))/D_prime
                y_0 = b**2 * (a**2 * y_a - x_a * Math.sqrt(D))/D_prime
                y_1 = b**2 * (a**2 * y_a + x_a * Math.sqrt(D))/D_prime

                triangle(
                    Math.floor(0.05 * width),
                    this.disco_position,
                    mouseX + x_0,
                    mouseY + y_0,
                    mouseX + x_1,
                    mouseY + y_1
                );
            }

            y_a = this.disco_position - mouseY;
            x_a = 0.95 * width - mouseX;
            D_prime = b**2 * x_a**2 + a**2 * y_a**2;
            D = D_prime - a**2 * b**2;

            if (D > 0) {

                x_a = 0.95 * width - mouseX;
                x_0 = a**2 * (b**2 * x_a + y_a * Math.sqrt(D))/D_prime
                x_1 = a**2 * (b**2 * x_a - y_a * Math.sqrt(D))/D_prime
                y_0 = b**2 * (a**2 * y_a - x_a * Math.sqrt(D))/D_prime
                y_1 = b**2 * (a**2 * y_a + x_a * Math.sqrt(D))/D_prime

                triangle(
                    Math.floor(0.95 * width),
                    this.disco_position,
                    mouseX + x_0,
                    mouseY + y_0,
                    mouseX + x_1,
                    mouseY + y_1
                );
            }
            pop();
            pop();
        }
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