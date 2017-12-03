

window.onload = function() {
	let headers = document.querySelectorAll("h3")

	for (header of headers) {
		console.log(header)
		let innerHtml = header.innerHTML
		header.innerHTML= innerHtml.replace(/\./g, "<span class=\"hack\">.</span>")
	}
}