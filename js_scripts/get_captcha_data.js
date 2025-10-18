window.getCaptchaData = () => {
    return new Promise((resolve, reject) => {
        try {
            console.log("Starting getCaptchaData function");
            
            let canvas = document.createElement('canvas');
            let ctx = canvas.getContext('2d');
            
            // Check if description element exists
            let descElement = document.querySelector('.rc-imageselect-desc-wrapper');
            if (!descElement) {
                console.error("Description element not found");
                reject('Description element not found');
                return;
            }
            let comment = descElement.innerText.replace(/\n/g, ' ');
            console.log("Comment extracted:", comment);

            let img4x4 = document.querySelector('img.rc-image-tile-44');
            if (!img4x4) {
                console.log("4x4 image not found, checking for 3x3 table");
                
                let table3x3 = document.querySelector('table.rc-imageselect-table-33 > tbody');
                if (!table3x3) {
                    console.error("Neither 4x4 nor 3x3 captcha elements found");
                    reject('Can not find reCAPTCHA elements');
                    return;
                }

                let initial3x3img = table3x3.querySelector('img.rc-image-tile-33');
                if (!initial3x3img) {
                    console.error("Initial 3x3 image not found");
                    reject('Initial 3x3 image not found');
                    return;
                }

                canvas.width = initial3x3img.naturalWidth;
                canvas.height = initial3x3img.naturalHeight;
                ctx.drawImage(initial3x3img, 0, 0);

                let updatedTiles = document.querySelectorAll('img.rc-image-tile-11');
                console.log("Found updated tiles:", updatedTiles.length);

                if (updatedTiles.length > 0) {
                    const pos = [
                        { x: 0, y: 0 }, { x: ctx.canvas.width / 3, y: 0 }, { x: ctx.canvas.width / 3 * 2, y: 0 },
                        { x: 0, y: ctx.canvas.height / 3 }, { x: ctx.canvas.width / 3, y: ctx.canvas.height / 3 }, { x: ctx.canvas.width / 3 * 2, y: ctx.canvas.height / 3 },
                        { x: 0, y: ctx.canvas.height / 3 * 2 }, { x: ctx.canvas.width / 3, y: ctx.canvas.height / 3 * 2 }, { x: ctx.canvas.width / 3 * 2, y: ctx.canvas.height / 3 * 2 }
                    ];
                    
                    updatedTiles.forEach((t, index) => {
                        console.log("Processing tile", index);
                        
                        // Check parent elements exist
                        if (!t.parentElement) {
                            console.error("Tile parent element not found");
                            return;
                        }
                        if (!t.parentElement.parentElement) {
                            console.error("Tile parent.parent element not found");
                            return;
                        }
                        if (!t.parentElement.parentElement.parentElement) {
                            console.error("Tile parent.parent.parent element not found");
                            return;
                        }
                        
                        const ind = t.parentElement.parentElement.parentElement.tabIndex;
                        console.log("Tile tabIndex:", ind);
                        
                        if (isNaN(ind) || ind < 3) {
                            console.error("Invalid tabIndex:", ind);
                            return;
                        }
                        
                        const posIndex = ind - 3;
                        if (posIndex < 0 || posIndex >= pos.length) {
                            console.error("Invalid position index:", posIndex);
                            return;
                        }
                        
                        if (!pos[posIndex]) {
                            console.error("Position object not found for index:", posIndex);
                            return;
                        }
                        
                        console.log("Drawing tile at position:", pos[posIndex]);
                        ctx.drawImage(t, pos[posIndex].x, pos[posIndex].y);
                    });
                }
                
                resolve({
                    rows: 3,
                    columns: 3,
                    type: 'GridTask',
                    comment,
                    body: canvas.toDataURL().replace(/^data:image\/?[A-z]*;base64,/, '')
                });
            } else {
                console.log("Processing 4x4 captcha");
                canvas.width = img4x4.naturalWidth;
                canvas.height = img4x4.naturalHeight;
                ctx.drawImage(img4x4, 0, 0);
                resolve({
                    rows: 4,
                    columns: 4,
                    comment,
                    body: canvas.toDataURL('image/jpeg', 0.8).replace(/^data:image\/jpeg;base64,/, ''),
                    type: 'GridTask'
                });
            }
        } catch (error) {
            console.error("Error in getCaptchaData:", error);
            reject(error);
        }
    });
};