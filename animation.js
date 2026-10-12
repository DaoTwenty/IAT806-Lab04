class FramesAnimation {

    // takes the image files and the speed. Images are drawn at their own size, never resized
    constructor(images, speed, x, y, rotation, size, isHeight, initFrame) {
        this.images = images;
        this.og_speed = speed;
        this.speed = speed;
        this.x = x;
        this.y = y;
        this.index = initFrame;
        this.active = true;
        this.rotation = rotation;
        if (isHeight) {
            this.height = size;
            this.width = Math.floor(this.height * this.images[0].width / this.images[0].height);
        } else {
            this.width = size;
            this.height = Math.floor(this.width * this.images[0].height / this.images[0].width);
        }
        this.frozen = false;
    }

    set_size(size, isHeight) {
        if (isHeight) {
            this.height = size;
            this.width = Math.floor(this.height * this.images[0].width / this.images[0].height);
        } else {
            this.width = size;
            this.height = Math.floor(this.width * this.images[0].height / this.images[0].width);
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

    get_index() {
        if (this.frozen == false) {
            this.index = Math.floor((frameCount / this.speed) % this.images.length);
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

    rotate(angle) {
        this.rotation += angle;
    }

    rotate_to(angle) {
        this.rotation = angle;
    }

    draw() {
        if (this.active == true) {
            push();
            imageMode(CENTER);
            this.get_index();
            translate(this.x, this.y);
            rotate(this.rotation);
            image(this.images[this.index], 0, 0, this.width, this.height);
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
