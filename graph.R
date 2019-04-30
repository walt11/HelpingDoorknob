# create table Forces(sample int auto_increment primary key,maxforce int, threshold int, dt DateTime);
library(RMySQL)
mydb = dbConnect(MySQL(),user='root',password='',dbname='project3',host='127.0.0.1')
while (TRUE){
	rs = dbSendQuery(mydb,"select * from Forces")
	data = fetch(rs,n=-1)
	xrange = range(data$sample)
	yrange = range((min(data$threshold)-20):(max(data$maxforce)+20))
	plot(xrange,yrange,type="n", xlab="Sample",ylab="Force")
	lines(data$sample,data$maxforce,type="b", lwd=1.5)
	lines(data$sample,data$threshold, type="b")
	abline(lm(data$maxforce ~ data$sample))
	title("Doorknob Max Force & Threshold")
	Sys.sleep(10)
}